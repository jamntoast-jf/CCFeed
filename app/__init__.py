import os
from flask import Flask
from config import Config
from app.db import init_db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    init_db(app.config["DB_PATH"])

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_favicon():
        favicon_path = os.path.join(app.static_folder, 'favicon.ico')
        return dict(has_favicon=os.path.isfile(favicon_path))

    return app
