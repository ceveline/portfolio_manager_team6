import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    # Use DATABASE_URL (e.g. Postgres) when provided, otherwise fall back to a
    # local SQLite database placed in the instance/ directory so the app can
    # run without extra environment configuration.
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or ("sqlite:///" + os.path.join(BASE_DIR, "instance", "app.db").replace('\\', '/'))
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SWAGGER = {
        "title": "Portfolio Manager API",
        "uiversion": 3,
    }
