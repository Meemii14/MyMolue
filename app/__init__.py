from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from sqlalchemy import inspect, text

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


def _ensure_sqlite_schema(app):
    """Add model columns that may be missing from an older SQLite database."""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "user" not in tables or "ride" not in tables:
        db.create_all()
        inspector = inspect(db.engine)

    migrations = {
        "user": {
            "wallet": "ALTER TABLE user ADD COLUMN wallet FLOAT DEFAULT 0",
            "rating": "ALTER TABLE user ADD COLUMN rating FLOAT DEFAULT 5",
            "is_verified": "ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0",
            "profile_picture": "ALTER TABLE user ADD COLUMN profile_picture VARCHAR(255) DEFAULT 'default.png'",
        },
        "ride": {
            "driver_id": "ALTER TABLE ride ADD COLUMN driver_id INTEGER",
            "counter_offer": "ALTER TABLE ride ADD COLUMN counter_offer FLOAT",
            "accepted_at": "ALTER TABLE ride ADD COLUMN accepted_at DATETIME",
            "created_at": "ALTER TABLE ride ADD COLUMN created_at DATETIME",
        },
    }

    for table, columns in migrations.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column, statement in columns.items():
            if column not in existing:
                db.session.execute(text(statement))

    db.session.commit()


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

    with app.app_context():
        db.create_all()
        _ensure_sqlite_schema(app)

    return app
