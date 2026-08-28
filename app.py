"""
Punto de entrada de Conecto+. Solo arma la app y registra los blueprints;
la lógica de cada módulo vive en routes/, la config en config.py, el acceso
a datos en extensions.py, y los helpers compartidos en security.py / utils.py.
"""
import os
from pathlib import Path

from flask import Flask

import config
import extensions
from extensions import query, execute  # re-exportado por compatibilidad con tests/test_app.py
from security import register_context_processor

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = Path(config.UPLOAD_FOLDER)

extensions.init_app(app)
register_context_processor(app)

from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.task_routes import task_bp
from routes.communication_routes import communication_bp
from routes.profile_routes import profile_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(task_bp)
app.register_blueprint(communication_bp)
app.register_blueprint(profile_bp)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
