from theflow.settings import settings as flowsettings

from main import demo  # noqa

GRADIO_SERVER_PORT = getattr(flowsettings, "GRADIO_SERVER_PORT")
AUTHENTICATION_METHOD = getattr(flowsettings, "AUTHENTICATION_METHOD")

if __name__ == "__main__":
    if AUTHENTICATION_METHOD == "KEYCLOAK":
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=GRADIO_SERVER_PORT)
