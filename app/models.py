from datetime import datetime

from flask_login import UserMixin
from app.database import db


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    fullname = db.Column(db.String(120), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    phone = db.Column(db.String(20), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    account_type = db.Column(db.String(20), nullable=False)

    wallet = db.Column(db.Float, default=0)

    rating = db.Column(db.Float, default=5)

    is_verified = db.Column(db.Boolean, default=False)

    profile_picture = db.Column(db.String(255), default="default.png")


class Ride(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    rider_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    driver_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    pickup = db.Column(db.String(200))

    destination = db.Column(db.String(200))

    fare_offer = db.Column(db.Float)

    counter_offer = db.Column(
        db.Float,
        nullable=True
    )
    status = db.Column(
        db.String(50),
        default="Pending"
    )

    accepted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now()
    )

    rider = db.relationship(
        "User",
        foreign_keys=[rider_id]
    )

    driver = db.relationship(
        "User",
        foreign_keys=[driver_id]
    )