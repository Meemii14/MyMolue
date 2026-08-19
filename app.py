import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "login"

RIDE_STATUSES = {"requested", "offer_received", "accepted", "arriving", "in_progress", "completed", "cancelled"}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="rider")
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rides_as_rider = db.relationship("Ride", foreign_keys="Ride.rider_id", backref="rider", lazy=True)
    rides_as_driver = db.relationship("Ride", foreign_keys="Ride.driver_id", backref="driver", lazy=True)
    offers = db.relationship("RideOffer", backref="driver", lazy=True, cascade="all, delete-orphan")

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    pickup = db.Column(db.String(255), nullable=False)
    destination = db.Column(db.String(255), nullable=False)
    rider_fare = db.Column(db.Float, nullable=False)
    accepted_fare = db.Column(db.Float, nullable=True)
    shared = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(30), default="requested", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    offers = db.relationship("RideOffer", backref="ride", lazy=True, cascade="all, delete-orphan")

class RideOffer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey("ride.id"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-this-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "mymolue.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    with app.app_context():
        db.create_all()
    return app

app = create_app()

def role_required(role):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                flash(f"Only {role}s can perform this action.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "rider")
        if role not in {"rider", "driver"}:
            role = "rider"
        if not all([name, email, phone, password]) or len(password) < 6:
            flash("Complete every field and use a password of at least 6 characters.", "error")
            return render_template("register.html")
        if User.query.filter((User.email == email) | (User.phone == phone)).first():
            flash("An account with that email or phone already exists.", "error")
            return render_template("register.html")
        user = User(name=name, email=email, phone=phone, role=role,
                    password_hash=bcrypt.generate_password_hash(password).decode("utf-8"))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    current_user.is_online = False
    db.session.commit()
    logout_user()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    rides = Ride.query.filter((Ride.rider_id == current_user.id) | (Ride.driver_id == current_user.id)).order_by(Ride.created_at.desc()).all()
    return render_template("dashboard.html", rides=rides)

@app.route("/driver/availability", methods=["POST"])
@role_required("driver")
def availability():
    current_user.is_online = request.form.get("online") == "true"
    db.session.commit()
    return jsonify({"online": current_user.is_online})

@app.route("/request-ride", methods=["POST"])
@role_required("rider")
def request_ride():
    pickup = request.form.get("pickup", "").strip()
    destination = request.form.get("destination", "").strip()
    try:
        fare = float(request.form.get("fare", "0"))
    except ValueError:
        fare = 0
    shared = request.form.get("shared") == "on"
    if not pickup or not destination or fare <= 0:
        flash("Enter valid pickup, destination and fare.", "error")
        return redirect(url_for("dashboard"))
    ride = Ride(rider_id=current_user.id, pickup=pickup, destination=destination,
                rider_fare=fare, shared=shared, status="requested")
    db.session.add(ride)
    db.session.commit()
    flash("Ride requested. Available drivers can now make offers.", "success")
    return redirect(url_for("dashboard"))

@app.route("/rides")
@role_required("driver")
def rides():
    active = Ride.query.filter_by(status="requested").order_by(Ride.created_at.desc()).all()
    return jsonify([{"id": r.id, "pickup": r.pickup, "destination": r.destination,
                     "fare": r.rider_fare, "shared": r.shared,
                     "offers": len(r.offers)} for r in active])

@app.route("/ride/<int:ride_id>/offer", methods=["POST"])
@role_required("driver")
def offer(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.status != "requested":
        flash("This ride is no longer accepting offers.", "error")
        return redirect(url_for("dashboard"))
    if not current_user.is_online:
        flash("Go online before making an offer.", "error")
        return redirect(url_for("dashboard"))
    try:
        amount = float(request.form.get("offer", "0"))
    except ValueError:
        amount = 0
    if amount <= 0:
        flash("Enter a valid offer.", "error")
        return redirect(url_for("dashboard"))
    existing = RideOffer.query.filter_by(ride_id=ride.id, driver_id=current_user.id).first()
    if existing:
        existing.amount = amount
        existing.status = "pending"
    else:
        db.session.add(RideOffer(ride_id=ride.id, driver_id=current_user.id, amount=amount))
    db.session.commit()
    flash("Your offer has been sent to the rider.", "success")
    return redirect(url_for("dashboard"))

@app.route("/ride/<int:ride_id>/offers")
@login_required
def ride_offers(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.rider_id != current_user.id:
        return jsonify({"error": "unauthorized"}), 403
    return jsonify([{"id": o.id, "driver": o.driver.name, "amount": o.amount,
                     "status": o.status} for o in ride.offers])

@app.route("/ride/<int:ride_id>/accept/<int:offer_id>", methods=["POST"])
@role_required("rider")
def accept_offer(ride_id, offer_id):
    ride = db.get_or_404(Ride, ride_id)
    selected = db.get_or_404(RideOffer, offer_id)
    if ride.rider_id != current_user.id or selected.ride_id != ride.id or ride.status != "requested":
        flash("This offer cannot be accepted.", "error")
        return redirect(url_for("dashboard"))
    ride.driver_id = selected.driver_id
    ride.accepted_fare = selected.amount
    ride.status = "accepted"
    selected.status = "accepted"
    for other in ride.offers:
        if other.id != selected.id:
            other.status = "rejected"
    db.session.commit()
    flash("Driver selected. Your ride is confirmed.", "success")
    return redirect(url_for("dashboard"))

@app.route("/ride/<int:ride_id>/status", methods=["POST"])
@login_required
def update_status(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if current_user.id not in {ride.rider_id, ride.driver_id}:
        return jsonify({"error": "unauthorized"}), 403
    new_status = request.form.get("status", "")
    transitions = {
        "accepted": {"arriving", "cancelled"},
        "arriving": {"in_progress", "cancelled"},
        "in_progress": {"completed", "cancelled"},
        "requested": {"cancelled"},
        "offer_received": {"cancelled"},
    }
    if new_status not in RIDE_STATUSES or new_status not in transitions.get(ride.status, set()):
        return jsonify({"error": "invalid status transition", "current": ride.status}), 400
    if new_status in {"arriving", "in_progress"} and current_user.id != ride.driver_id:
        return jsonify({"error": "only the assigned driver can update this status"}), 403
    if new_status == "completed" and current_user.id != ride.driver_id:
        return jsonify({"error": "only the assigned driver can complete a trip"}), 403
    ride.status = new_status
    if new_status in {"completed", "cancelled"} and ride.driver_id:
        ride.driver.is_online = True
    db.session.commit()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
