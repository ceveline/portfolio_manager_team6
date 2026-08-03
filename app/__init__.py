import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
try:
    from flask_migrate import Migrate
except ImportError:
    Migrate = None

from flasgger import Swagger

db = SQLAlchemy()
# If flask_migrate is available, create a Migrate instance; otherwise keep None
migrate = Migrate() if Migrate is not None else None


def create_app(config_object="app.config.Config"):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_object)

    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    # Ensure there's a default database URI so Flask-SQLAlchemy can initialize.
    # The config object may set SQLALCHEMY_DATABASE_URI to None (from env); if so,
    # override with a filesystem sqlite DB so init_app doesn't fail. Tests can still
    # override with an in-memory database after calling create_app.
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            f"sqlite:///{os.path.join(app.root_path, '..', 'instance', 'portfolio.db')}"
        )

    db.init_app(app)
    if migrate is not None:
        migrate.init_app(app, db)

    Swagger(app)

    from app.routes import api
    app.register_blueprint(api)

    @app.route("/")
    def index():
        return render_template("index.html")

    # Import here to avoid circular import
    from app.models import User

    with app.app_context():
        db.create_all()

        # Create a unique user for profile
        if not User.query.filter_by(email="johndoe@gmail.com").first():
            db.session.add(
                User(
                    first_name="John",
                    last_name="Doe",
                    email="johndoe@gmail.com",
                    account_balance=110000
                )
            )
            db.session.commit()

    return app