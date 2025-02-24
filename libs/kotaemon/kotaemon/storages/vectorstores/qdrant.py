import logging
import threading
import time
from typing import Any, List, Optional, cast

from .base import LlamaIndexVectorStore


class QdrantVectorStore(LlamaIndexVectorStore):
    _li_class = None

    def _get_li_class(self):
        try:
            from llama_index.vector_stores.qdrant import (
                QdrantVectorStore as LIQdrantVectorStore,
            )
        except ImportError:
            raise ImportError(
                "Please install missing package: "
                "'pip install llama-index-vector-stores-qdrant'"
            )

        return LIQdrantVectorStore

    def __init__(
        self,
        collection_name,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        client_kwargs: Optional[dict] = None,
        keep_alive: Optional[bool] = False,
        keep_alive_interval: Optional[int] = 600,
        **kwargs: Any,
    ):
        self._collection_name = collection_name
        self._url = url
        self._api_key = api_key
        self._client_kwargs = client_kwargs
        self._kwargs = kwargs

        super().__init__(
            collection_name=collection_name,
            url=url,
            api_key=api_key,
            client_kwargs=client_kwargs,
            **kwargs,
        )
        from llama_index.vector_stores.qdrant import (
            QdrantVectorStore as LIQdrantVectorStore,
        )

        self._client = cast(LIQdrantVectorStore, self._client)

        if keep_alive:
            self._keep_alive_interval = keep_alive_interval
            self._keep_alive_thread = threading.Thread(
                target=self._keep_qdrant_alive, daemon=True
            )
            self._keep_alive_thread.start()

    def delete(self, ids: List[str], **kwargs):
        """Delete vector embeddings from vector stores

        Args:
            ids: List of ids of the embeddings to be deleted
            kwargs: meant for vectorstore-specific parameters
        """
        from qdrant_client import models

        self._client.client.delete(
            collection_name=self._collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            ),
            **kwargs,
        )

    def drop(self):
        """Delete entire collection from vector stores"""
        self._client.client.delete_collection(self._collection_name)

    def count(self) -> int:
        return self._client.client.count(
            collection_name=self._collection_name, exact=True
        ).count

    def __persist_flow__(self):
        return {
            "collection_name": self._collection_name,
            "url": self._url,
            "api_key": self._api_key,
            "client_kwargs": self._client_kwargs,
            **self._kwargs,
        }

    def _keep_qdrant_alive(self):
        """Ping Qdrant periodically to keep the connection alive."""
        while True:
            try:
                self._client._client.get_collections()
                logging.debug("Qdrant keep-alive successful.")
            except Exception as e:
                logging.error("Qdrant keep-alive error:", e)
            time.sleep(self._keep_alive_interval)
