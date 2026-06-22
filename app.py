import math
import os
import secrets
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import get_db, init_db, seed_db, get_expenses_for_period

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
VALID_CATEGORIES = set(CATEGORIES)


def is_valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


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

    today = date.today()
    default_start = today.replace(day=1).isoformat()
    default_end   = today.isoformat()

    start_date = request.args.get("start_date", default_start)
    end_date   = request.args.get("end_date",   default_end)

    if not is_valid_date(start_date) or not is_valid_date(end_date):
        start_date, end_date = default_start, default_end

    filter_error = None
    if start_date > end_date:
        filter_error = "Start date must be on or before end date."

    db = get_db()

    row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    name     = row["name"]
    initials = "".join(p[0].upper() for p in name.split()[:2])
    joined   = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    user = {
        "name":         name,
        "initials":     initials,
        "email":        row["email"],
        "member_since": joined.strftime("%B %d, %Y"),
    }

    expense_rows = [] if filter_error else get_expenses_for_period(
        db, session["user_id"], start_date, end_date
    )
    db.close()

    transactions = []
    cat_totals   = {}
    total_spent  = 0.0
    for r in expense_rows:
        transactions.append({
            "date":        datetime.strptime(r["date"], "%Y-%m-%d").strftime("%b %d, %Y"),
            "description": r["description"],
            "category":    r["category"],
            "amount":      r["amount"],
        })
        cat_totals[r["category"]] = cat_totals.get(r["category"], 0) + r["amount"]
        total_spent += r["amount"]

    top_category = max(cat_totals, key=cat_totals.get) if cat_totals else "—"
    stats = {
        "total_spent":       total_spent,
        "transaction_count": len(expense_rows),
        "top_category":      top_category,
    }

    categories = [
        {"name": cat, "amount": amt, "pct": round(amt / total_spent * 100)}
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    ] if total_spent > 0 else []

    return render_template(
        "profile.html",
        user=user, stats=stats,
        transactions=transactions, categories=categories,
        start_date=start_date, end_date=end_date,
        filter_error=filter_error,
    )


@app.route("/analytics")
def analytics():
    guard = login_required()
    if guard:
        return guard
    return render_template("analytics.html")


def _render_add_form(error=None, amount="", category="", expense_date="", description=""):
    return render_template(
        "add_expense.html",
        error=error,
        amount=amount,
        category=category,
        date=expense_date,
        description=description,
        categories=CATEGORIES,
        csrf_token=session.get("csrf_token", ""),
        today=date.today().isoformat(),
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    guard = login_required()
    if guard:
        return guard

    if request.method == "GET":
        session["csrf_token"] = secrets.token_hex(16)
        return _render_add_form()

    if request.form.get("csrf_token") != session.get("csrf_token"):
        return _render_add_form(error="Invalid request. Please try again.")

    amount_raw   = request.form.get("amount", "").strip()
    category     = request.form.get("category", "").strip()
    expense_date = request.form.get("date", "").strip()
    description  = request.form.get("description", "").strip()[:200]

    try:
        amount = float(amount_raw)
        if amount <= 0 or not math.isfinite(amount) or amount > 1_000_000:
            raise ValueError
    except ValueError:
        return _render_add_form("Amount must be a positive number no greater than 1,000,000.",
                                amount_raw, category, expense_date, description)

    if not is_valid_date(expense_date):
        return _render_add_form("Please enter a valid date.",
                                amount_raw, category, expense_date, description)

    if category not in VALID_CATEGORIES:
        return _render_add_form("Please select a valid category.",
                                amount_raw, category, expense_date, description)

    db = get_db()
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (session.get("user_id"), amount, category, expense_date, description or None)
    )
    db.commit()
    db.close()
    return redirect(url_for("profile"))


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
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
