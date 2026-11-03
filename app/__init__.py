import logging

from flask import Flask

from .config import Config
from .errors import register_error_handlers
from .extensions import db
from .routes import api


def create_app(config_object: type[Config] = Config) -> Flask:
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    app.register_blueprint(api, url_prefix="/")
    register_error_handlers(app)

    with app.app_context():
        db.create_all()

    return app
