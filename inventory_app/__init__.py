import os

from flask import Flask, g, request
from sqlalchemy.pool import NullPool

from .auth import current_user_can, load_current_user
from .backup_service import ensure_daily_backup
from .models import User, db
from .phase2_service import audit_log, ensure_permissions_seed, ensure_phase2_schema
from .routes import main_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY", "troque-esta-chave-em-producao")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///estoque.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Pool settings para SQLite - desabilitar pool para evitar resource warnings
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"check_same_thread": False},
        "poolclass": NullPool,  # Disable connection pooling for SQLite
    }

    db.init_app(app)

    with app.app_context():
        db.create_all()

        # Cria usuario admin padrao apenas na primeira execucao.
        if User.query.count() == 0:
            admin = User(username="admin", role="admin", is_active=True)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

        ensure_phase2_schema()
        ensure_permissions_seed()

        ensure_daily_backup()
        
        # Remove session to avoid resource warnings
        db.session.remove()

    @app.before_request
    def _load_user():
        load_current_user()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Remove database session at the end of request"""
        db.session.remove()

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user"), "current_user_can": current_user_can}

    @app.after_request
    def _audit_mutations(response):
        try:
            user = g.get("user")
            if user and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                if request.endpoint != "static":
                    audit_log(
                        username=user.username,
                        action=f"request:{request.method}",
                        endpoint=request.endpoint,
                        path=request.path,
                        method=request.method,
                        status_code=response.status_code,
                    )
        except Exception:
            # Nao interrompe o fluxo principal por falha de auditoria.
            pass
        return response

    app.register_blueprint(main_bp)
    return app
