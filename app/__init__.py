"""
Flask application factory
"""
from flask import Flask, request
from flask_cors import CORS
from app.config import config_by_name
from mongoengine import connect
from app.utils.logging_config import logger, log_request


def create_app(config_name='development'):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config_by_name[config_name])

    logger.info(f"Starting Transaction Service with config: {config_name}")

    CORS(app)
    connect(
    db=app.config.get('MONGODB_DB', 'devopsshowcase'),
    username=app.config.get('MONGODB_USER', 'appuser'),
    password=app.config.get('MONGODB_PASSWORD', 'apppassword'),
    host=app.config.get('MONGODB_HOST', 'localhost'),
    port=int(app.config.get('MONGODB_PORT', 27017)),
    authentication_source=app.config.get('MONGODB_AUTH_SOURCE', 'devopsshowcase')
    )
    logger.info(f"Connected to MongoDB: {app.config.get('MONGODB_HOST')}:{app.config.get('MONGODB_PORT')}/{app.config.get('MONGODB_DB')}")

    # Request logging middleware
    @app.before_request
    def log_request_info():
        log_request(request.path, request.method, request.get_json(silent=True))

    # Register blueprints
    from app.routes.transaction_routes import transaction_bp
    app.register_blueprint(transaction_bp, url_prefix='/api/transactions')
    logger.info("Registered transaction routes at /api/transactions")

    # Register error handlers
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)

    logger.info("Transaction Service initialized successfully")
    return app

