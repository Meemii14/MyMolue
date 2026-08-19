import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="rider")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rides_as_rider = db.relationship("Ride", foreign_keys="Ride.rider_id", backref="rider", lazy=True)
    rides_as_driver = db.relationship("Ride", foreign_keys="Ride.driver_id", backref="driver", lazy=True)

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    pickup = db.Column(db.String(255), nullable=False)
    destination = db.Column(db.String(255), nullable=False)
    rider_fare = db.Column(db.Float, nullable=False)
    accepted_fare = db.Column(db.Float, nullable=True)
    driver_offer = db.Column(db.Float, nullable=True)
    shared = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(30), default="requested")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-this-secret")
    db_path = os.path.join(BASE_DIR, "mymolue.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    with app.app_context():
        db.create_all()
    return app

app = create_app()

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
        if not all([name, email, phone, password]):
            flash("Please complete every field.", "error")
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
    logout_user()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    rides = Ride.query.filter((Ride.rider_id == current_user.id) | (Ride.driver_id == current_user.id)).order_by(Ride.created_at.desc()).all()
    return render_template("dashboard.html", rides=rides)

@app.route("/request-ride", methods=["POST"])
@login_required
def request_ride():
    if current_user.role != "rider":
        flash("Only riders can request rides.", "error")
        return redirect(url_for("dashboard"))
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
    flash("Ride requested. Drivers can now make offers.", "success")
    return redirect(url_for("dashboard"))

@app.route("/rides")
def rides():
    active = Ride.query.filter_by(status="requested").order_by(Ride.created_at.desc()).all()
    return jsonify([{"id": r.id, "pickup": r.pickup, "destination": r.destination,
                     "fare": r.rider_fare, "shared": r.shared, "status": r.status} for r in active])

@app.route("/ride/<int:ride_id>/offer", methods=["POST"])
@login_required
def offer(ride_id):
    if current_user.role != "driver":
        flash("Only drivers can make offers.", "error")
        return redirect(url_for("dashboard"))
    ride = db.get_or_404(Ride, ride_id)
    try:
        amount = float(request.form.get("offer", "0"))
    except ValueError:
        amount = 0
    if amount <= 0 or ride.status != "requested":
        flash("Invalid offer or ride is no longer available.", "error")
        return redirect(url_for("dashboard"))
    ride.driver_offer = amount
    ride.driver_id = current_user.id
    ride.status = "offer_received"
    db.session.commit()
    flash("Your offer has been sent to the rider.", "success")
    return redirect(url_for("dashboard"))

@app.route("/ride/<int:ride_id>/accept", methods=["POST"])
@login_required
def accept_offer(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.rider_id != current_user.id or ride.status != "offer_received":
        flash("You cannot accept this offer.", "error")
        return redirect(url_for("dashboard"))
    ride.accepted_fare = ride.driver_offer
    ride.status = "accepted"
    db.session.commit()
    flash("Driver offer accepted. Your ride is confirmed.", "success")
    return redirect(url_for("dashboard"))

@app.route("/ride/<int:ride_id>/status", methods=["POST"])
@login_required
def update_status(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if current_user.id not in {ride.rider_id, ride.driver_id}:
        return jsonify({"error": "unauthorized"}), 403
    status = request.form.get("status", "")
    allowed = {"accepted", "arriving", "in_progress", "completed", "cancelled"}
    if status not in allowed:
        return jsonify({"error": "invalid status"}), 400
    ride.status = status
    db.session.commit()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
