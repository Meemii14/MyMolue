from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import bcrypt
from app.database import db
from app.models import User, Ride


auth = Blueprint("auth", __name__)


@auth.route("/")
def home():
    return render_template("index.html")


@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        account_type = request.form.get("account_type", "").strip()

        if not all([fullname, email, phone, password, account_type]):
            flash("Please complete all fields.", "error")
            return redirect(url_for("auth.register"))

        if account_type not in {"Rider", "Driver"}:
            flash("Please choose a valid account type.", "error")
            return redirect(url_for("auth.register"))

        existing_user = User.query.filter(
            (User.email == email) | (User.phone == phone)
        ).first()

        if existing_user:
            flash("Email or phone number already exists.", "error")
            return redirect(url_for("auth.register"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(
            fullname=fullname,
            email=email,
            phone=phone,
            password=hashed_password,
            account_type=account_type,
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            if user.account_type == "Rider":
                return redirect(url_for("auth.rider_dashboard"))
            return redirect(url_for("auth.driver_dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@auth.route("/rider-dashboard")
@login_required
def rider_dashboard():
    rides = Ride.query.filter_by(rider_id=current_user.id).order_by(Ride.id.desc()).all()
    completed = Ride.query.filter_by(rider_id=current_user.id, status="Completed").count()
    pending = Ride.query.filter_by(rider_id=current_user.id, status="Pending").count()
    return render_template(
        "rider_dashboard.html",
        current_user=current_user,
        rides=rides,
        completed=completed,
        pending=pending,
    )


@auth.route("/driver-dashboard")
@login_required
def driver_dashboard():
    rides = Ride.query.filter_by(status="Pending").order_by(Ride.id.desc()).all()
    return render_template("driver_dashboard.html", current_user=current_user, rides=rides)


@auth.route("/request-ride", methods=["POST"])
@login_required
def request_ride():
    if current_user.account_type != "Rider":
        flash("Only riders can request rides.", "error")
        return redirect(url_for("auth.driver_dashboard"))

    pickup = request.form.get("pickup", "").strip()
    destination = request.form.get("destination", "").strip()
    fare_text = request.form.get("fare_offer", "").strip()

    try:
        fare_offer = float(fare_text)
        if fare_offer <= 0:
            raise ValueError
    except ValueError:
        flash("Please enter a valid fare offer.", "error")
        return redirect(url_for("auth.rider_dashboard"))

    if not pickup or not destination:
        flash("Pickup and destination are required.", "error")
        return redirect(url_for("auth.rider_dashboard"))

    ride = Ride(
        rider_id=current_user.id,
        pickup=pickup,
        destination=destination,
        fare_offer=fare_offer,
        status="Pending",
    )
    db.session.add(ride)
    db.session.commit()
    flash("Ride request submitted successfully!", "success")
    return redirect(url_for("auth.rider_dashboard"))


@auth.route("/accept-ride/<int:ride_id>", methods=["POST"])
@login_required
def accept_ride(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if current_user.account_type != "Driver":
        flash("Only drivers can accept rides.", "error")
        return redirect(url_for("auth.rider_dashboard"))
    if ride.status != "Pending":
        flash("This ride is no longer available.", "error")
        return redirect(url_for("auth.driver_dashboard"))

    ride.driver_id = current_user.id
    ride.status = "Accepted"
    ride.accepted_at = db.func.now()
    db.session.commit()
    flash("Ride accepted successfully!", "success")
    return redirect(url_for("auth.driver_dashboard"))


@auth.route("/counter-offer/<int:ride_id>", methods=["POST"])
@login_required
def counter_offer(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if current_user.account_type != "Driver" or ride.status != "Pending":
        flash("This ride is no longer available.", "error")
        return redirect(url_for("auth.driver_dashboard"))

    try:
        counter = float(request.form.get("counter_offer", ""))
        if counter <= 0:
            raise ValueError
    except ValueError:
        flash("Please enter a valid counter offer.", "error")
        return redirect(url_for("auth.driver_dashboard"))

    ride.driver_id = current_user.id
    ride.counter_offer = counter
    ride.status = "Counter Offered"
    db.session.commit()
    flash("Counter offer sent successfully!", "success")
    return redirect(url_for("auth.driver_dashboard"))


@auth.route("/accept-counter/<int:ride_id>", methods=["POST"])
@login_required
def accept_counter(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.rider_id != current_user.id:
        flash("Unauthorized.", "error")
        return redirect(url_for("auth.rider_dashboard"))
    if ride.status != "Counter Offered" or ride.counter_offer is None:
        flash("This counter offer is no longer available.", "error")
        return redirect(url_for("auth.rider_dashboard"))

    ride.fare_offer = ride.counter_offer
    ride.status = "Accepted"
    db.session.commit()
    flash("Counter offer accepted!", "success")
    return redirect(url_for("auth.rider_dashboard"))


@auth.route("/reject-counter/<int:ride_id>", methods=["POST"])
@login_required
def reject_counter(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.rider_id != current_user.id:
        flash("Unauthorized.", "error")
        return redirect(url_for("auth.rider_dashboard"))

    ride.driver_id = None
    ride.counter_offer = None
    ride.status = "Pending"
    db.session.commit()
    flash("Counter offer rejected.", "success")
    return redirect(url_for("auth.rider_dashboard"))


@auth.route("/driver-arriving/<int:ride_id>", methods=["POST"])
@login_required
def driver_arriving(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.driver_id != current_user.id:
        flash("Unauthorized.", "error")
        return redirect(url_for("auth.driver_dashboard"))
    if ride.status != "Accepted":
        flash("The trip must be accepted first.", "error")
        return redirect(url_for("auth.driver_dashboard"))

    ride.status = "Arriving"
    db.session.commit()
    flash("Passenger has been notified that you're arriving.", "success")
    return redirect(url_for("auth.driver_dashboard"))


@auth.route("/start-trip/<int:ride_id>", methods=["POST"])
@login_required
def start_trip(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.driver_id != current_user.id:
        flash("Unauthorized.", "error")
        return redirect(url_for("auth.driver_dashboard"))
    if ride.status != "Arriving":
        flash("The driver must be marked as arriving first.", "error")
        return redirect(url_for("auth.driver_dashboard"))

    ride.status = "In Progress"
    db.session.commit()
    flash("Trip started.", "success")
    return redirect(url_for("auth.driver_dashboard"))


@auth.route("/complete-trip/<int:ride_id>", methods=["POST"])
@login_required
def complete_trip(ride_id):
    ride = db.get_or_404(Ride, ride_id)
    if ride.driver_id != current_user.id:
        flash("Unauthorized.", "error")
        return redirect(url_for("auth.driver_dashboard"))
    if ride.status != "In Progress":
        flash("Trip is not currently in progress.", "error")
        return redirect(url_for("auth.driver_dashboard"))

    ride.status = "Completed"
    current_user.wallet = (current_user.wallet or 0) + (ride.fare_offer or 0)
    db.session.commit()
    flash("Trip completed successfully!", "success")
    return redirect(url_for("auth.driver_dashboard"))


@auth.route("/wallet")
@login_required
def wallet():
    return render_template("wallet.html", current_user=current_user)


@auth.route("/ride-history")
@login_required
def ride_history():
    rides = Ride.query.filter_by(rider_id=current_user.id).order_by(Ride.id.desc()).all()
    return render_template("ride_history.html", rides=rides, current_user=current_user)


@auth.route("/shared-rides")
@login_required
def shared_rides():
    return render_template("shared_rides.html")


@auth.route("/profile")
@login_required
def profile():
    return render_template("profile.html", current_user=current_user)


@auth.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@auth.route("/book-ride")
@login_required
def book_ride():
    return render_template("book_ride.html", current_user=current_user)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
