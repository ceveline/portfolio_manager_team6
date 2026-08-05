import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    # Use DATABASE_URL when provided. Alternatively, allow constructing a
    # MySQL URI from MYSQL_* env vars (supports optional MYSQL_SOCKET).
    mysql_user = os.environ.get("MYSQL_USER", "root")
    mysql_password = os.environ.get("MYSQL_PASSWORD", "")
    mysql_host = os.environ.get("MYSQL_HOST", "localhost")
    mysql_port = os.environ.get("MYSQL_PORT")
    mysql_db = os.environ.get("MYSQL_DB", "portfolio_manager")
    mysql_socket = os.environ.get("MYSQL_SOCKET")

    if os.environ.get("DATABASE_URL"):
        SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        try:
            from urllib.parse import quote_plus
        except Exception:
            from urllib import quote_plus

        pwd = quote_plus(mysql_password) if mysql_password else ""
        pwd_part = f":{pwd}@" if mysql_password else "@"
        port_part = f":{mysql_port}" if mysql_port else ""
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{mysql_user}{pwd_part}{mysql_host}{port_part}/{mysql_db}"
        )
        if mysql_socket:
            SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"unix_socket": mysql_socket}}
        else:
            SQLALCHEMY_ENGINE_OPTIONS = {}

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SWAGGER = {
        "title": "Portfolio Manager API",
        "uiversion": 3,
    }
