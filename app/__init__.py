import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flasgger import Swagger

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_object="app.config.Config"):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_object)

    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
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