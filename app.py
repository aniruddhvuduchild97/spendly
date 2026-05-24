from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"


def login_required():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get('user_id'):
            return redirect(url_for('dashboard'))
        return render_template("register.html")

    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        db.close()
        return render_template("register.html", error="An account with that email already exists.")

    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password))
    )
    db.commit()
    session["user_id"] = cursor.lastrowid
    session["user_name"] = name
    db.close()
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get('user_id'):
            return redirect(url_for('dashboard'))
        return render_template("login.html")

    email = request.form["email"]
    password = request.form["password"]

    db = get_db()
    user = db.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    db.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/dashboard")
def dashboard():
    guard = login_required()
    if guard:
        return guard
    return render_template("dashboard.html", name=session["user_name"])


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    guard = login_required()
    if guard:
        return guard

    user = {
        "name": "Demo User",
        "initials": "DU",
        "email": "demo@spendly.com",
        "member_since": "January 1, 2026",
    }
    stats = {
        "total_spent": 339.49,
        "transaction_count": 8,
        "top_category": "Bills",
    }
    transactions = [
        {"date": "May 17, 2026", "description": "Groceries",             "category": "Food",          "amount": 22.00},
        {"date": "May 14, 2026", "description": "Miscellaneous",          "category": "Other",         "amount": 9.99},
        {"date": "May 12, 2026", "description": "Clothing",               "category": "Shopping",      "amount": 85.00},
        {"date": "May 10, 2026", "description": "Streaming subscription", "category": "Entertainment", "amount": 15.00},
        {"date": "May 7, 2026",  "description": "Vitamins",               "category": "Health",        "amount": 30.00},
        {"date": "May 5, 2026",  "description": "Electricity bill",       "category": "Bills",         "amount": 120.00},
        {"date": "May 3, 2026",  "description": "Monthly bus pass",       "category": "Transport",     "amount": 45.00},
        {"date": "May 1, 2026",  "description": "Lunch at cafe",          "category": "Food",          "amount": 12.50},
    ]
    categories = [
        {"name": "Bills",         "amount": 120.00, "pct": 35},
        {"name": "Shopping",      "amount": 85.00,  "pct": 25},
        {"name": "Transport",     "amount": 45.00,  "pct": 13},
        {"name": "Food",          "amount": 34.50,  "pct": 10},
        {"name": "Health",        "amount": 30.00,  "pct": 9},
        {"name": "Entertainment", "amount": 15.00,  "pct": 4},
        {"name": "Other",         "amount": 9.99,   "pct": 3},
    ]
    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
