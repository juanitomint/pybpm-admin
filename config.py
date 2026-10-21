import os

from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))


def as_bool(value):
    if value:
        return value.lower() in ["true", "yes", "on", "1"]
    return False


class Config:
    """Base configuration class. All settings loaded from environment variables."""

    # pybpm-api backend URL — identity provider (auth) + model persistence.
    PYBPM_API_URL = os.environ.get("PYBPM_API_URL", "http://localhost:5000/api/v1")

    # Port the editor FastAPI app listens on.
    APP_PORT = int(os.environ.get("APP_PORT", "8080"))

    # Environment (development / production) — controls debug mode and logging verbosity.
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")
    DEBUG = as_bool(os.environ.get("DEBUG", "false"))

    # Static asset root — the `static/` directory with Oryx editor JS/CSS/images.
    STATIC_ROOT = os.path.join(basedir, "static")

    # Admin URL prefix — all admin API routes live under this path (matches legacy `/admin/*`).
    ADMIN_URL_PREFIX = "/admin"

    # Morty sandbox API — executes scripts in a sandboxed environment.
    MORTY_API_URL = os.environ.get(
        "MORTY_API_URL", "http://localhost:5000/api/v1/morty"
    )


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    DEBUG = True


def get_config_by_name(name: str) -> type[Config]:
    """Return the configuration class for a given env name."""
    mapping = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": Config,
    }
    cls = mapping.get(name)
    if cls is None:
        raise ValueError(f"Unknown config name: {name}")
    return cls
