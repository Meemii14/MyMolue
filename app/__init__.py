from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

from app.database import db
from app.models import User


bcrypt = Bcrypt()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app():
    project_root = Path(__file__).resolve().parent.parent
    instance_path = project_root / "instance"
    instance_path.mkdir(parents=True, exist_ok=True)

    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
        instance_path=str(instance_path),
    )

    app.config.update(
        SECRET_KEY="mymolue-dev-secret-change-in-production",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{instance_path / 'mymolue.db'}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from app.auth import auth
    app.register_blueprint(auth)

    # Create missing tables automatically for this prototype.
    # Existing tables are left untouched by create_all().
    with app.app_context():
        db.create_all()

    return app
