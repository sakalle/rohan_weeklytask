from flask import Flask, jsonify
from pydantic import ValidationError

from .ai import ClassificationError
from .schemas import model_errors


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation(error: ValidationError):
        return jsonify({"error": "validation failed", "details": model_errors(error)}), 400

    @app.errorhandler(ClassificationError)
    def handle_classification_error(error: ClassificationError):
        return jsonify({"error": "AI classification unavailable", "message": str(error)}), 503

    @app.errorhandler(404)
    def handle_not_found(_error):
        return jsonify({"error": "resource not found"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_error):
        return jsonify({"error": "method not allowed"}), 405

    @app.errorhandler(500)
    def handle_internal_error(_error):
        app.logger.exception("Unhandled server error")
        return jsonify({"error": "internal server error"}), 500
