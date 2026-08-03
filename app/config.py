import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    # Use DATABASE_URL when provided. Alternatively, allow constructing a
    # MySQL URI from MYSQL_* env vars (supports optional MYSQL_SOCKET).
    mysql_user = os.environ.get("MYSQL_USER")
    mysql_password = os.environ.get("MYSQL_PASSWORD")
    mysql_host = os.environ.get("MYSQL_HOST")
    mysql_port = os.environ.get("MYSQL_PORT")
    mysql_db = os.environ.get("MYSQL_DB")
    mysql_socket = os.environ.get("MYSQL_SOCKET")

    if os.environ.get("DATABASE_URL"):
        SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
        SQLALCHEMY_ENGINE_OPTIONS = {}
    elif mysql_user and mysql_password and mysql_host and mysql_db:
        try:
            from urllib.parse import quote_plus
        except Exception:
            from urllib import quote_plus

        pwd = quote_plus(mysql_password)
        port_part = f":{mysql_port}" if mysql_port else ""
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{mysql_user}:{pwd}@{mysql_host}{port_part}/{mysql_db}"
        )
        if mysql_socket:
            SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"unix_socket": mysql_socket}}
        else:
            SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_DATABASE_URI = (
            "sqlite:///" + os.path.join(BASE_DIR, "instance", "app.db").replace('\\', '/')
        )
        SQLALCHEMY_ENGINE_OPTIONS = {}

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SWAGGER = {
        "title": "Portfolio Manager API",
        "uiversion": 3,
    }
