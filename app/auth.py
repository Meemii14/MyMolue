from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from app import bcrypt
from app.database import db
from app.models import User, Ride


auth = Blueprint("auth", __name__)


# ==========================
# Home
# ==========================

@auth.route("/")
def home():
    return render_template("index.html")


# ==========================
# Register
# ==========================

@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        account_type = request.form["account_type"]

        existing_user = User.query.filter(
            (User.email == email) |
            (User.phone == phone)
        ).first()

        if existing_user:

            flash(
                "Email or phone number already exists.",
                "error"
            )

            return redirect(url_for("auth.register"))

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        new_user = User(
            fullname=fullname,
            email=email,
            phone=phone,
            password=hashed_password,
            account_type=account_type
        )

        db.session.add(new_user)
        db.session.commit()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ==========================
# Login
# ==========================

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(
            email=email
        ).first()

        if user and bcrypt.check_password_hash(
            user.password,
            password
        ):

            login_user(user)

            if user.account_type == "Rider":

                return redirect(
                    url_for("auth.rider_dashboard")
                )

            if user.account_type == "Driver":

                return redirect(
                    url_for("auth.driver_dashboard")
                )

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template("login.html")


# ==========================
# Rider Dashboard
# ==========================

@auth.route("/rider-dashboard")
@login_required
def rider_dashboard():

    rides = Ride.query.filter_by(
        rider_id=current_user.id
    ).order_by(
        Ride.id.desc()
    ).all()

    completed = Ride.query.filter_by(
        rider_id=current_user.id,
        status="Completed"
    ).count()

    pending = Ride.query.filter_by(
        rider_id=current_user.id,
        status="Pending"
    ).count()

    return render_template(
        "rider_dashboard.html",
        current_user=current_user,
        rides=rides,
        completed=completed,
        pending=pending
    )


# ==========================
# Driver Dashboard
# ==========================


# ==========================
# Request Ride
# ==========================

@auth.route("/request-ride", methods=["POST"])
@login_required
def request_ride():

    pickup = request.form["pickup"]
    destination = request.form["destination"]
    fare_offer = request.form["fare_offer"]

    ride = Ride(
        rider_id=current_user.id,
        pickup=pickup,
        destination=destination,
        fare_offer=fare_offer,
        status="Pending"
    )

    db.session.add(ride)
    db.session.commit()

    flash(
        "Ride request submitted successfully!",
        "success"
    )

    return redirect(
        url_for("auth.rider_dashboard")
    )
@auth.route("/accept-ride/<int:ride_id>", methods=["POST"])
@login_required
def accept_ride(ride_id):

    ride = Ride.query.get_or_404(ride_id)

    if ride.status != "Pending":

        flash(
            "This ride has already been accepted.",
            "error"
        )

        return redirect(
            url_for("auth.driver_dashboard")
        )

    ride.driver_id = current_user.id
    ride.status = "Accepted"

    db.session.commit()

    flash(
        "Ride accepted successfully!",
        "success"
    )
@auth.route("/counter-offer/<int:ride_id>", methods=["POST"])
@login_required
def counter_offer(ride_id):

    ride = Ride.query.get_or_404(ride_id)

    if ride.status != "Pending":

        flash(
            "This ride is no longer available.",
            "error"
        )

        return redirect(
            url_for("auth.driver_dashboard")
        )

    ride.driver_id = current_user.id

    ride.counter_offer = float(
        request.form["counter_offer"]
    )

    ride.status = "Counter Offered"

    db.session.commit()

    flash(
        "Counter offer sent successfully!",
        "success"
    )

    return redirect(
        url_for("auth.driver_dashboard")
    )
@auth.route("/accept-counter/<int:ride_id>", methods=["POST"])
@login_required
def accept_counter(ride_id):

    ride = Ride.query.get_or_404(ride_id)

    if ride.rider_id != current_user.id:

        flash(
            "Unauthorized.",
            "error"
        )

        return redirect(
            url_for("auth.rider_dashboard")
        )

    ride.fare_offer = ride.counter_offer
    ride.status = "Accepted"

    db.session.commit()

    flash(
        "Counter offer accepted!",
        "success"
    )

    return redirect(
        url_for("auth.rider_dashboard")
    )

    return redirect(
        url_for("auth.rider_dashboard")
    )
    db.session.commit()

    flash(
        "Counter offer sent successfully!",
        "success"
    )
@auth.route("/reject-counter/<int:ride_id>", methods=["POST"])
@login_required
def reject_counter(ride_id):

    ride = Ride.query.get_or_404(ride_id)

    if ride.rider_id != current_user.id:

        flash(
            "Unauthorized.",
            "error"
        )

        return redirect(
            url_for("auth.rider_dashboard")
        )

    ride.driver_id = None
    ride.counter_offer = None
    ride.status = "Pending"

    db.session.commit()

    flash(
        "Counter offer rejected.",
        "success"
    )
@auth.route("/driver-arriving/<int:ride_id>", methods=["POST"])
@login_required
def driver_arriving(ride_id):

    ride = Ride.query.get_or_404(ride_id)

    if ride.driver_id != current_user.id:

        flash(
            "Unauthorized.",
            "error"
        )

        return redirect(
            url_for("auth.driver_dashboard")
        )

    ride.status = "Arriving"

    db.session.commit()

    flash(
        "Passenger has been notified that you're arriving.",
        "success"
    )

    return redirect(
        url_for("auth.driver_dashboard")
    )
@auth.route("/start-trip/<int:ride_id>", methods=["POST"])
@login_required
def start_trip(ride_id):

    ride = Ride.query.get_or_404(ride_id)

    if ride.driver_id != current_user.id:

        flash(
            "Unauthorized.",
            "error"
        )

        return redirect(
            url_for("auth.driver_dashboard")
        )

    ride.status = "In Progress"

    db.session.commit()

    flash(
        "Trip started.",
        "success"
    )

    return redirect(
        url_for("auth.driver_dashboard")
    )


@auth.route("/complete-trip/<int:ride_id>", methods=["POST"])
@login_required
def complete_trip(ride_id):

    ride = Ride.query.get_or_404(ride_id)

    if ride.driver_id != current_user.id:

        flash(
            "Unauthorized.",
            "error"
        )

        return redirect(
            url_for("auth.driver_dashboard")
        )

    ride.status = "Completed"

    current_user.wallet += ride.fare_offer

    db.session.commit()

    flash(
        "Trip completed successfully!",
        "success"
    )

    return redirect(
        url_for("auth.driver_dashboard")
    )
    return redirect(
        url_for("auth.rider_dashboard")
    )
    return redirect(
        url_for("auth.driver_dashboard")
    )
    return redirect(
        url_for("auth.driver_dashboard")
    )

    db.session.commit()

    flash(
        "Ride accepted successfully!",
        "success"
    )

    return redirect(
        url_for("auth.driver_dashboard")
    )

# ==========================
# Logout
# ==========================
@auth.route("/wallet")
@login_required
def wallet():
    return render_template(
    "wallet.html",
    current_user=current_user
)


@auth.route("/ride-history")
@login_required
def ride_history():

    rides = Ride.query.filter_by(
        rider_id=current_user.id
    ).order_by(
        Ride.id.desc()
    ).all()

    return render_template(
        "ride_history.html",
        rides=rides,
        current_user=current_user
    )


@auth.route("/shared-rides")
@login_required
def shared_rides():
    return render_template("shared_rides.html")


@auth.route("/profile")
@login_required
def profile():

    return render_template(
        "profile.html",
        current_user=current_user
    )


@auth.route("/settings")
@login_required
def settings():
    return render_template("settings.html")
@auth.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("auth.login")
    )
@auth.route("/book-ride")
@login_required
def book_ride():

    return render_template(
        "book_ride.html",
        current_user=current_user
    )
@auth.route("/driver-dashboard")
@login_required
def driver_dashboard():

    rides = Ride.query.filter_by(
        status="Pending"
    ).all()

    return render_template(
        "driver_dashboard.html",
        current_user=current_user,
        rides=rides
    )