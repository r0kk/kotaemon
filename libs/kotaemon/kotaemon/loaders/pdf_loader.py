import base64
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

from decouple import config
from fsspec import AbstractFileSystem
from llama_index.readers.file import PDFReader
from PIL import Image

from kotaemon.base import Document

PDF_LOADER_DPI = config("PDF_LOADER_DPI", default=40, cast=int)


def get_page_thumbnails(
    file_path: Path, pages: list[int], dpi: int = PDF_LOADER_DPI
) -> List[Image.Image]:
    """Get image thumbnails of the pages in the PDF file.

    Args:
        file_path (Path): path to the image file
        page_number (list[int]): list of page numbers to extract

    Returns:
        list[Image.Image]: list of page thumbnails
    """
    img: Image.Image
    suffix = file_path.suffix.lower()
    assert suffix == ".pdf", "This function only supports PDF files."
    try:
        import fitz
    except ImportError:
        raise ImportError("Please install PyMuPDF: 'pip install PyMuPDF'")

    doc = fitz.open(file_path)

    output_imgs = []
    for page_number in pages:
        page = doc.load_page(page_number)
        pm = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
        output_imgs.append(convert_image_to_base64(img))

    return output_imgs


def convert_image_to_base64(img: Image.Image) -> str:
    # convert the image into base64
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
    img_base64 = f"data:image/png;base64,{img_base64}"

    return img_base64


def load_pdf_data(
    file: Path, extra_info: Optional[Dict], fs: Optional[AbstractFileSystem]
) -> List[Document]:
    reader = PDFReader(return_full_document=False)
    return reader.load_data(file, extra_info, fs)


class PDFThumbnailReader(PDFReader):
    """PDF parser with thumbnail for each page."""

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
        timeout: Optional[float] = 300.0,
    ) -> List[Document]:
        """Parse file.

        Parameters
        ----------
        file : Path
            Path to the file to be parsed.
        extra_info : Optional[Dict], optional
            Extra information to be added to the document metadata, by default None
        fs : Optional[AbstractFileSystem], optional
            Filesystem to use, by default None
        timeout : Optional[float], optional
            Timeout for the process, by default 300.0.

        Returns
        -------
        List[Document]
            List of documents.

        Raises
        ------
        TimeoutError
            If the process takes too long to complete.

        """
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(load_pdf_data, file, extra_info, fs)
            process = None

            # Retrieve the underlying process
            for pid, p in executor._processes.items():
                process = p
                break

            try:
                documents = future.result(timeout=timeout)
            except TimeoutError as e:
                if process:
                    process.terminate()
                    process.join()
                raise e

        page_numbers_str = []
        filtered_docs = []
        is_int_page_number: dict[str, bool] = {}

        for doc in documents:
            if "page_label" in doc.metadata:
                page_num_str = doc.metadata["page_label"]
                page_numbers_str.append(page_num_str)
                try:
                    _ = int(page_num_str)
                    is_int_page_number[page_num_str] = True
                    filtered_docs.append(doc)
                except ValueError:
                    is_int_page_number[page_num_str] = False
                    continue

        documents = filtered_docs
        page_numbers = list(range(len(page_numbers_str)))

        print("Page numbers:", len(page_numbers))
        page_thumbnails = get_page_thumbnails(file, page_numbers)

        documents.extend(
            [
                Document(
                    text="Page thumbnail",
                    metadata={
                        "image_origin": page_thumbnail,
                        "type": "thumbnail",
                        "page_label": page_number,
                        **(extra_info if extra_info is not None else {}),
                    },
                )
                for (page_thumbnail, page_number) in zip(
                    page_thumbnails, page_numbers_str
                )
                if is_int_page_number[page_number]
            ]
        )

        return documents
