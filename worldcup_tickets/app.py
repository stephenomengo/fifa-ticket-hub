import sqlite3
import os
import stripe
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g

app = Flask(__name__)
app.secret_key = "worldcup-secret-key-change-me"
DB = "worldcup.db"

# Stripe configuration - keys come from environment variables (set on Render)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

# Map team names to ISO 3166-1 alpha-2 codes for flag images (flagcdn.com)
COUNTRY_CODES = {
    "Brazil": "br", "Argentina": "ar", "Germany": "de", "France": "fr",
    "Spain": "es", "Portugal": "pt", "England": "gb-eng", "Italy": "it",
    "USA": "us", "Mexico": "mx", "Japan": "jp", "South Korea": "kr",
    "Netherlands": "nl", "Belgium": "be", "Croatia": "hr", "Morocco": "ma",
    "Uruguay": "uy", "Switzerland": "ch", "Senegal": "sn", "Ghana": "gh",
    "Cameroon": "cm", "Canada": "ca", "Poland": "pl", "Serbia": "rs",
    "Wales": "gb-wls", "Australia": "au", "Tunisia": "tn", "Denmark": "dk",
    "Ecuador": "ec", "Qatar": "qa", "Saudi Arabia": "sa", "Costa Rica": "cr",
    "Iran": "ir", "Sweden": "se", "Colombia": "co", "Chile": "cl",
    "Nigeria": "ng", "Egypt": "eg", "Ivory Coast": "ci", "Norway": "no",
}


def flag_code(team_name):
    return COUNTRY_CODES.get(team_name, "un")  # 'un' = UN flag fallback


# Stadium photo keywords -> Unsplash source images (royalty-free)
STADIUM_IMAGES = {
    "Maracana Stadium, Rio de Janeiro": "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800&q=80",
    "Allianz Arena, Munich": "https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800&q=80",
    "Santiago Bernabeu, Madrid": "https://images.unsplash.com/photo-1489944440615-453fc2b6a9a9?w=800&q=80",
    "Wembley Stadium, London": "https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800&q=80",
    "MetLife Stadium, New Jersey": "https://images.unsplash.com/photo-1577223625816-7546f13df25d?w=800&q=80",
    "Tokyo National Stadium, Tokyo": "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800&q=80",
}
DEFAULT_STADIUM_IMAGE = "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800&q=80"


def stadium_image(name):
    return STADIUM_IMAGES.get(name, DEFAULT_STADIUM_IMAGE)


@app.context_processor
def inject_helpers():
    return dict(flag_code=flag_code, stadium_image=stadium_image)


# ---------- Database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB)
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team1 TEXT NOT NULL,
        team2 TEXT NOT NULL,
        stadium TEXT NOT NULL,
        match_date TEXT NOT NULL,
        price REAL NOT NULL,
        total_seats INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        match_id INTEGER NOT NULL,
        seat_numbers TEXT NOT NULL,
        num_seats INTEGER NOT NULL,
        total_price REAL NOT NULL,
        booking_date TEXT NOT NULL,
        payment_status TEXT DEFAULT 'pending',
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (match_id) REFERENCES matches (id)
    )
    """)

    # Migration: add payment_status column if upgrading from older schema
    cur.execute("PRAGMA table_info(bookings)")
    columns = [c[1] for c in cur.fetchall()]
    if "payment_status" not in columns:
        cur.execute("ALTER TABLE bookings ADD COLUMN payment_status TEXT DEFAULT 'paid'")

    # Seed admin user
    cur.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
            ("admin", "admin123", 1),
        )

    # Seed sample matches
    cur.execute("SELECT COUNT(*) FROM matches")
    if cur.fetchone()[0] == 0:
        sample_matches = [
            ("Brazil", "Argentina", "Maracana Stadium, Rio de Janeiro", "2026-06-20 18:00", 150.0, 60),
            ("Germany", "France", "Allianz Arena, Munich", "2026-06-22 20:00", 130.0, 60),
            ("Spain", "Portugal", "Santiago Bernabeu, Madrid", "2026-06-24 17:00", 140.0, 60),
            ("England", "Italy", "Wembley Stadium, London", "2026-06-26 19:30", 160.0, 60),
            ("USA", "Mexico", "MetLife Stadium, New Jersey", "2026-06-28 16:00", 120.0, 60),
            ("Japan", "South Korea", "Tokyo National Stadium, Tokyo", "2026-06-30 15:00", 110.0, 60),
        ]
        cur.executemany(
            "INSERT INTO matches (team1, team2, stadium, match_date, price, total_seats) VALUES (?, ?, ?, ?, ?, ?)",
            sample_matches,
        )

    db.commit()
    db.close()


# ---------- Auth helpers ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session or not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


# ---------- Routes ----------
@app.route("/")
def index():
    db = get_db()
    matches = db.execute("SELECT * FROM matches ORDER BY match_date").fetchall()
    return render_template("index.html", matches=matches)


@app.route("/match/<int:match_id>")
def match_detail(match_id):
    db = get_db()
    match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        flash("Match not found.", "danger")
        return redirect(url_for("index"))

    # Get booked seats for this match
    bookings = db.execute(
        "SELECT seat_numbers FROM bookings WHERE match_id = ?", (match_id,)
    ).fetchall()
    booked_seats = set()
    for b in bookings:
        booked_seats.update(b["seat_numbers"].split(","))

    return render_template("match_detail.html", match=match, booked_seats=booked_seats)


@app.route("/book/<int:match_id>", methods=["POST"])
@login_required
def book_seats(match_id):
    db = get_db()
    match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        flash("Match not found.", "danger")
        return redirect(url_for("index"))

    selected_seats = request.form.getlist("seats")
    if not selected_seats:
        flash("Please select at least one seat.", "warning")
        return redirect(url_for("match_detail", match_id=match_id))

    # Check seats not already booked
    bookings = db.execute(
        "SELECT seat_numbers FROM bookings WHERE match_id = ?", (match_id,)
    ).fetchall()
    booked_seats = set()
    for b in bookings:
        booked_seats.update(b["seat_numbers"].split(","))

    for seat in selected_seats:
        if seat in booked_seats:
            flash(f"Seat {seat} is already booked. Please choose again.", "danger")
            return redirect(url_for("match_detail", match_id=match_id))

    num_seats = len(selected_seats)
    total_price = num_seats * match["price"]
    seat_numbers_str = ",".join(selected_seats)
    booking_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        """INSERT INTO bookings (user_id, match_id, seat_numbers, num_seats, total_price, booking_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session["user_id"], match_id, seat_numbers_str, num_seats, total_price, booking_date),
    )
    db.commit()

    booking_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return redirect(url_for("payment", booking_id=booking_id))


@app.route("/payment/<int:booking_id>", methods=["GET", "POST"])
@login_required
def payment(booking_id):
    db = get_db()
    booking = db.execute(
        """SELECT bookings.*, matches.team1, matches.team2, matches.stadium, matches.match_date
           FROM bookings JOIN matches ON bookings.match_id = matches.id
           WHERE bookings.id = ? AND bookings.user_id = ?""",
        (booking_id, session["user_id"]),
    ).fetchone()

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("index"))

    if booking["payment_status"] == "paid":
        return redirect(url_for("checkout", booking_id=booking_id))

    if request.method == "POST":
        if not stripe.api_key:
            flash("Payment processing is not configured yet.", "danger")
            return redirect(url_for("payment", booking_id=booking_id))

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(booking["total_price"] * 100),  # cents
                        "product_data": {
                            "name": f"{booking['team1']} vs {booking['team2']} - {booking['num_seats']} ticket(s)",
                            "description": f"{booking['stadium']} | Seats: {booking['seat_numbers']}",
                        },
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=url_for("payment_success", booking_id=booking_id, _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=url_for("payment", booking_id=booking_id, _external=True),
                metadata={"booking_id": str(booking_id)},
            )
        except Exception as e:
            flash(f"Could not start payment: {e}", "danger")
            return redirect(url_for("payment", booking_id=booking_id))

        return redirect(checkout_session.url, code=303)

    return render_template("payment.html", booking=booking, stripe_configured=bool(stripe.api_key))


@app.route("/payment-success/<int:booking_id>")
@login_required
def payment_success(booking_id):
    db = get_db()
    booking = db.execute(
        "SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, session["user_id"])
    ).fetchone()

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("index"))

    session_id = request.args.get("session_id")
    if session_id and stripe.api_key:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            if checkout_session.payment_status == "paid":
                db.execute("UPDATE bookings SET payment_status = 'paid' WHERE id = ?", (booking_id,))
                db.commit()
                flash("Payment successful!", "success")
            else:
                flash("Payment not completed.", "warning")
        except Exception as e:
            flash(f"Could not verify payment: {e}", "danger")
    else:
        flash("Missing payment confirmation.", "danger")

    return redirect(url_for("checkout", booking_id=booking_id))


@app.route("/checkout/<int:booking_id>")
@login_required
def checkout(booking_id):
    db = get_db()
    booking = db.execute(
        """SELECT bookings.*, matches.team1, matches.team2, matches.stadium, matches.match_date
           FROM bookings JOIN matches ON bookings.match_id = matches.id
           WHERE bookings.id = ? AND bookings.user_id = ?""",
        (booking_id, session["user_id"]),
    ).fetchone()

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("index"))

    if booking["payment_status"] != "paid":
        return redirect(url_for("payment", booking_id=booking_id))

    return render_template("checkout.html", booking=booking)


@app.route("/my-tickets")
@login_required
def my_tickets():
    db = get_db()
    bookings = db.execute(
        """SELECT bookings.*, matches.team1, matches.team2, matches.stadium, matches.match_date
           FROM bookings JOIN matches ON bookings.match_id = matches.id
           WHERE bookings.user_id = ? AND bookings.payment_status = 'paid'
           ORDER BY bookings.booking_date DESC""",
        (session["user_id"],),
    ).fetchall()
    return render_template("my_tickets.html", bookings=bookings)


# ---------- Auth routes ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if not username or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "warning")
            return redirect(url_for("register"))

        db = get_db()
        existing = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("Username already taken.", "danger")
            return redirect(url_for("register"))

        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        db.commit()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?", (username, password)
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome back, {username}!", "success")
            if session["is_admin"]:
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# ---------- Admin routes ----------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    matches = db.execute("SELECT * FROM matches ORDER BY match_date").fetchall()

    total_bookings = db.execute("SELECT COUNT(*) FROM bookings WHERE payment_status='paid'").fetchone()[0]
    total_revenue = db.execute("SELECT COALESCE(SUM(total_price), 0) FROM bookings WHERE payment_status='paid'").fetchone()[0]
    total_seats_sold = db.execute("SELECT COALESCE(SUM(num_seats), 0) FROM bookings WHERE payment_status='paid'").fetchone()[0]

    return render_template(
        "admin_dashboard.html",
        matches=matches,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        total_seats_sold=total_seats_sold,
    )


@app.route("/admin/add-match", methods=["GET", "POST"])
@admin_required
def add_match():
    if request.method == "POST":
        team1 = request.form["team1"].strip()
        team2 = request.form["team2"].strip()
        stadium = request.form["stadium"].strip()
        match_date = request.form["match_date"].strip()
        price = request.form["price"]
        total_seats = request.form["total_seats"]

        db = get_db()
        db.execute(
            """INSERT INTO matches (team1, team2, stadium, match_date, price, total_seats)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (team1, team2, stadium, match_date, price, total_seats),
        )
        db.commit()
        flash("Match added successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_match.html")


@app.route("/admin/edit-match/<int:match_id>", methods=["GET", "POST"])
@admin_required
def edit_match(match_id):
    db = get_db()
    match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        flash("Match not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        team1 = request.form["team1"].strip()
        team2 = request.form["team2"].strip()
        stadium = request.form["stadium"].strip()
        match_date = request.form["match_date"].strip()
        price = request.form["price"]
        total_seats = request.form["total_seats"]

        db.execute(
            """UPDATE matches SET team1=?, team2=?, stadium=?, match_date=?, price=?, total_seats=?
               WHERE id=?""",
            (team1, team2, stadium, match_date, price, total_seats, match_id),
        )
        db.commit()
        flash("Match updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_match.html", match=match)


@app.route("/admin/delete-match/<int:match_id>")
@admin_required
def delete_match(match_id):
    db = get_db()
    db.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    db.execute("DELETE FROM bookings WHERE match_id = ?", (match_id,))
    db.commit()
    flash("Match deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    db = get_db()
    bookings = db.execute(
        """SELECT bookings.*, users.username, matches.team1, matches.team2, matches.match_date
           FROM bookings
           JOIN users ON bookings.user_id = users.id
           JOIN matches ON bookings.match_id = matches.id
           WHERE bookings.payment_status = 'paid'
           ORDER BY bookings.booking_date DESC"""
    ).fetchall()
    return render_template("admin_bookings.html", bookings=bookings)


init_db()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
