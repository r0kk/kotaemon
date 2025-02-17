import os

import sentry_sdk
from theflow.settings import settings as flowsettings

sentry_sdk.init(
    dsn=getattr(flowsettings, "SENTRY_DSN"),
    release=getattr(flowsettings, "KH_APP_VERSION"),
    environment=getattr(flowsettings, "SENTRY_ENVIRONMENT"),
    traces_sampler=getattr(flowsettings, "SENTRY_TRACES_SAMPLER"),
    traces_sample_rate=getattr(flowsettings, "SENTRY_TRACES_SAMPLE_RATE"),
    send_default_pii=True,
)

KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
KH_GRADIO_SHARE = getattr(flowsettings, "KH_GRADIO_SHARE", False)
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)
# override GRADIO_TEMP_DIR if it's not set
if GRADIO_TEMP_DIR is None:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR


from ktem.main import App  # noqa

app = App()
demo = app.make()
demo.queue().launch(
    favicon_path=app._favicon,
    inbrowser=True,
    allowed_paths=[
        "libs/ktem/ktem/assets",
        GRADIO_TEMP_DIR,
    ],
    share=KH_GRADIO_SHARE,
    app_kwargs={"docs_url": "/docs"},
)
