import os
from typing import List

import gradiologin as grlogin
import sentry_sdk
from decouple import config
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from ktem.main import App  # noqa
from starlette.requests import Request
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
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)
AUTHENTICATION_METHOD = config("AUTHENTICATION_METHOD")
KH_GRADIO_SHARE = getattr(flowsettings, "KH_GRADIO_SHARE", False)

# override GRADIO_TEMP_DIR if it's not set
if GRADIO_TEMP_DIR is None:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR

gradio_app = App()
demo = gradio_app.make()

REQUIRED_ROLE = getattr(flowsettings, "REQUIRED_ROLE")


def user_has_required_role(roles: List[str]) -> bool:
    return REQUIRED_ROLE in roles


INSUFFICIENT_PERMISSIONS_HTML = """
<html>
<head><title>Access Denied</title></head>
<body style="font-family: Arial; text-align: center; margin-top: 100px;">
    <h1>Access Denied</h1>
    <p>You don't have sufficient permissions.</p>
    <a href="{logout_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Sign Out</a>
    <p><small>Redirecting in <span id="countdown">5</span>s...</small></p>
    <script>
        let c = 5;
        setInterval(() => {{
            c--;
            document.getElementById('countdown').textContent = c;
            if (c <= 0) location.href = '{logout_url}';
        }}, 1000);
    </script>
</body>
</html>
"""


if AUTHENTICATION_METHOD == "KEYCLOAK":
    app = FastAPI()
    KEYCLOAK_SERVER_URL = getattr(flowsettings, "KEYCLOAK_SERVER_URL")
    KEYCLOAK_REALM = getattr(flowsettings, "KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID = getattr(flowsettings, "KEYCLOAK_CLIENT_ID")
    KEYCLOAK_CLIENT_SECRET = getattr(flowsettings, "KEYCLOAK_CLIENT_SECRET")
    KEYCLOAK_LOGOUT_URL = getattr(flowsettings, "KEYCLOAK_LOGOUT_URL")

    grlogin.register(
        name="Email",
        server_metadata_url=(
            f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/"
            ".well-known/openid-configuration"
        ),
        client_id=KEYCLOAK_CLIENT_ID,
        client_secret=KEYCLOAK_CLIENT_SECRET,
        client_kwargs={
            "scope": "openid email profile roles",
        },
    )

    @app.middleware("http")
    async def enforce_role_check(request: Request, call_next):
        if request.url.path.startswith("/app"):
            user = request.scope.get("session", {}).get("user")
            if user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")

            if not user_has_required_role(user["realm_access"]["roles"]):
                request.session.clear()
                html_content = INSUFFICIENT_PERMISSIONS_HTML.format(
                    logout_url=KEYCLOAK_LOGOUT_URL
                )
                return HTMLResponse(content=html_content, status_code=403)

        return await call_next(request)

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        response = RedirectResponse(url=KEYCLOAK_LOGOUT_URL)
        response.delete_cookie("session", path="/app")
        return response

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(gradio_app._favicon)

    grlogin.mount_gradio_app(
        app,
        demo,
        "/app",
        allowed_paths=[
            "libs/ktem/ktem/assets",
            GRADIO_TEMP_DIR,
        ],
    )
    os.environ["GR_FILE_ROOT_PATH"] = "/app"

elif AUTHENTICATION_METHOD == "GRADIO_LOGIN":
    demo.queue().launch(
        favicon_path=gradio_app._favicon,
        inbrowser=True,
        allowed_paths=[
            "libs/ktem/ktem/assets",
            GRADIO_TEMP_DIR,
        ],
        share=KH_GRADIO_SHARE,
    )
else:
    raise ValueError(f"Unsupported authentication method: {AUTHENTICATION_METHOD}")
