"""
tests/test_add_expense.py

Test suite for the Add Expense feature (Step 07).

Spec: .claude/specs/07-add-expense.md

All test logic is derived exclusively from the spec's Definition of Done,
Routes section, and Rules for implementation — not from the source code.

--- DB isolation note ---
get_db() in database/db.py always connects to the file-based spendly.db
regardless of app.config['DATABASE'].  Each fixture therefore creates a
unique user (UUID-based email) and removes all inserted rows in teardown so
tests never interfere with each other or with the seed_db() demo data.
"""

import re
import uuid
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    """Return a collision-free email address for each test invocation."""
    return f"addexp-{uuid.uuid4().hex[:12]}@spendly-test.com"


def _today() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Flask application configured for testing; DB file is shared (see note)."""
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-07',
        'WTF_CSRF_ENABLED': False,
    })
    with flask_app.app_context():
        init_db()   # idempotent — creates tables only if absent
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """
    Creates an isolated test user, logs in, and yields (test_client, user_id, email).
    Cleans up all expenses and the user row on teardown.
    """
    email = _unique_email()
    password = "TestPass999"

    with flask_app.app_context():
        db = get_db()
        try:
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Add Expense Tester", email, generate_password_hash(password)),
            )
            user_id = cur.lastrowid
            db.commit()
        finally:
            db.close()

    client.post("/login", data={"email": email, "password": password})

    yield client, user_id, email

    # Teardown — remove all rows created during this test
    with flask_app.app_context():
        db = get_db()
        try:
            db.execute(
                "DELETE FROM expenses WHERE user_id = ?",
                (user_id,),
            )
            db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Convenience: a minimal valid POST payload
# ---------------------------------------------------------------------------

def _valid_payload(**overrides):
    base = {
        "amount": "19.99",
        "category": "Food",
        "date": _today(),
        "description": "Test lunch",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:

    def test_unauthenticated_get_redirects_to_login(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Unauthenticated GET /expenses/add must return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login for unauthenticated GET"
        )

    def test_unauthenticated_post_redirects_to_login(self, client):
        response = client.post("/expenses/add", data=_valid_payload())
        assert response.status_code == 302, (
            "Unauthenticated POST /expenses/add must return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login for unauthenticated POST"
        )

    def test_authenticated_get_returns_200(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert response.status_code == 200, (
            "Authenticated GET /expenses/add must return HTTP 200"
        )


# ---------------------------------------------------------------------------
# 2. Form rendering on GET
# ---------------------------------------------------------------------------

class TestFormRendering:

    def test_form_has_amount_field(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'name="amount"' in response.data, (
            "Add-expense form must contain an input with name='amount'"
        )

    def test_amount_field_uses_type_number(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'type="number"' in response.data, (
            "Amount input must use type='number'"
        )

    def test_amount_field_has_correct_step_attribute(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'step="0.01"' in response.data, (
            "Amount input must have step='0.01'"
        )

    def test_amount_field_has_correct_min_attribute(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'min="0.01"' in response.data, (
            "Amount input must have min='0.01'"
        )

    def test_form_has_category_select(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'name="category"' in response.data, (
            "Add-expense form must contain a select with name='category'"
        )

    def test_form_has_date_field(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'name="date"' in response.data, (
            "Add-expense form must contain an input with name='date'"
        )

    def test_date_field_uses_type_date(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'type="date"' in response.data, (
            "Date input must use type='date'"
        )

    def test_form_has_description_field(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'name="description"' in response.data, (
            "Add-expense form must contain an input with name='description'"
        )

    def test_form_has_submit_button_labelled_add_expense(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b"Add Expense" in response.data, (
            "Submit button must be labelled 'Add Expense'"
        )

    def test_form_uses_post_method(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'method="POST"' in response.data or b'method="post"' in response.data, (
            "Add-expense form must use method='POST'"
        )

    def test_form_action_points_to_add_expense_route(self, auth_client):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert b'/expenses/add' in response.data, (
            "Form action must point to /expenses/add"
        )

    def test_template_extends_base(self, auth_client):
        """Page must render full HTML, not a bare fragment — implies base.html inheritance."""
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        # base.html renders a <html> root and includes the shared navbar
        assert b'<html' in response.data or b'<!DOCTYPE' in response.data, (
            "Template must extend base.html (full HTML document expected)"
        )


# ---------------------------------------------------------------------------
# 3. Date pre-population on GET
# ---------------------------------------------------------------------------

class TestDatePrepopulation:

    def test_date_field_pre_populated_with_today(self, auth_client):
        tc, _, _ = auth_client
        today = _today()
        response = tc.get("/expenses/add")
        assert today.encode() in response.data, (
            f"Date field must be pre-populated with today's date ({today}) on GET"
        )


# ---------------------------------------------------------------------------
# 4. Category options
# ---------------------------------------------------------------------------

class TestCategoryOptions:

    @pytest.mark.parametrize("category", [
        "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
    ])
    def test_all_seven_category_options_present(self, auth_client, category):
        tc, _, _ = auth_client
        response = tc.get("/expenses/add")
        assert category.encode() in response.data, (
            f"Category option '{category}' must be present in the form select"
        )


# ---------------------------------------------------------------------------
# 5. Happy path POST — redirect and DB side effect
# ---------------------------------------------------------------------------

class TestHappyPath:

    def test_valid_post_redirects_to_profile(self, auth_client):
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload())
        assert response.status_code == 302, (
            "Valid POST /expenses/add must redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "Successful POST must redirect to /profile"
        )

    def test_valid_post_inserts_row_into_db(self, auth_client, app):
        tc, user_id, _ = auth_client
        payload = _valid_payload(
            amount="42.50",
            category="Transport",
            date="2025-03-15",
            description="Bus fare",
        )
        tc.post("/expenses/add", data=payload)

        with app.app_context():
            db = get_db()
            try:
                row = db.execute(
                    "SELECT amount, category, date, description"
                    " FROM expenses WHERE user_id = ? AND description = ?",
                    (user_id, "Bus fare"),
                ).fetchone()
            finally:
                db.close()

        assert row is not None, (
            "A row for the submitted expense must exist in the DB after POST"
        )
        assert row["amount"] == 42.50, (
            "Stored amount must match submitted value"
        )
        assert row["category"] == "Transport", (
            "Stored category must match submitted value"
        )
        assert row["date"] == "2025-03-15", (
            "Stored date must match submitted value"
        )

    def test_valid_post_stores_correct_user_id(self, auth_client, app):
        tc, user_id, _ = auth_client
        payload = _valid_payload(description="ownership-check")
        tc.post("/expenses/add", data=payload)

        with app.app_context():
            db = get_db()
            try:
                row = db.execute(
                    "SELECT user_id FROM expenses WHERE user_id = ? AND description = ?",
                    (user_id, "ownership-check"),
                ).fetchone()
            finally:
                db.close()

        assert row is not None, "Expense row must be found for the logged-in user"
        assert row["user_id"] == user_id, (
            "Stored user_id must equal the session user's id"
        )

    def test_valid_post_without_description_succeeds(self, auth_client, app):
        """Description is optional; omitting it must not cause a validation error."""
        tc, user_id, _ = auth_client
        payload = {
            "amount": "5.00",
            "category": "Other",
            "date": _today(),
            "description": "",
        }
        response = tc.post("/expenses/add", data=payload)
        assert response.status_code == 302, (
            "POST with empty description must still succeed and redirect"
        )

        with app.app_context():
            db = get_db()
            try:
                row = db.execute(
                    "SELECT id FROM expenses WHERE user_id = ? AND amount = ? AND category = ?",
                    (user_id, 5.00, "Other"),
                ).fetchone()
            finally:
                db.close()

        assert row is not None, "Expense with no description must still be persisted"

    def test_new_expense_visible_on_profile_page_after_redirect(self, auth_client):
        """Follow the redirect and confirm the description appears in the profile."""
        tc, _, _ = auth_client
        unique_desc = f"visible-{uuid.uuid4().hex[:8]}"
        payload = _valid_payload(description=unique_desc, date="2025-06-01")

        # POST then follow the redirect chain
        response = tc.post("/expenses/add", data=payload, follow_redirects=True)
        assert response.status_code == 200, (
            "Following the redirect after POST must land on a 200 page"
        )
        assert unique_desc.encode() in response.data, (
            "Newly added expense description must be visible after redirect to /profile"
        )

    def test_valid_post_does_not_rerender_form(self, auth_client):
        """On success the route must redirect, never re-render the add-expense form."""
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload())
        # A re-render would return 200; success must be 302
        assert response.status_code != 200, (
            "Successful POST must not re-render the form (must redirect)"
        )


# ---------------------------------------------------------------------------
# 6. Validation errors — amount
# ---------------------------------------------------------------------------

class TestAmountValidation:

    @pytest.mark.parametrize("bad_amount", [
        "",        # missing / empty
        "0",       # zero
        "0.00",    # zero as decimal
        "-1",      # negative
        "-0.01",   # negative fraction
        "abc",     # non-numeric string
        "twelve",  # non-numeric word
        " ",       # whitespace only
    ])
    def test_invalid_amount_rerenders_form_with_200(self, auth_client, bad_amount):
        tc, _, _ = auth_client
        payload = _valid_payload(amount=bad_amount)
        response = tc.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            f"Invalid amount {bad_amount!r} must re-render the form (200), not redirect"
        )

    @pytest.mark.parametrize("bad_amount", [
        "", "0", "0.00", "-1", "abc",
    ])
    def test_invalid_amount_shows_error_message(self, auth_client, bad_amount):
        tc, _, _ = auth_client
        payload = _valid_payload(amount=bad_amount)
        response = tc.post("/expenses/add", data=payload)
        # The error message must be present somewhere in the page
        assert (
            b"Amount must be a positive number" in response.data
            or b"error" in response.data.lower()
            or b"invalid" in response.data.lower()
        ), (
            f"An error message must appear when amount={bad_amount!r} is submitted"
        )

    def test_missing_amount_shows_error_message(self, auth_client):
        tc, _, _ = auth_client
        payload = _valid_payload()
        del payload["amount"]
        response = tc.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            "Missing amount field must re-render the form with 200"
        )
        assert b"Amount must be a positive number" in response.data, (
            "Error message must state the amount must be a positive number"
        )

    def test_zero_amount_shows_error_message(self, auth_client):
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload(amount="0"))
        assert response.status_code == 200
        assert b"Amount must be a positive number" in response.data, (
            "Zero amount must produce the positive-number error message"
        )

    def test_invalid_amount_does_not_insert_row(self, auth_client, app):
        tc, user_id, _ = auth_client
        unique_desc = f"should-not-exist-{uuid.uuid4().hex[:8]}"
        tc.post("/expenses/add", data=_valid_payload(amount="abc", description=unique_desc))

        with app.app_context():
            db = get_db()
            try:
                row = db.execute(
                    "SELECT id FROM expenses WHERE user_id = ? AND description = ?",
                    (user_id, unique_desc),
                ).fetchone()
            finally:
                db.close()

        assert row is None, "No DB row must be inserted when amount validation fails"


# ---------------------------------------------------------------------------
# 7. Validation errors — date
# ---------------------------------------------------------------------------

class TestDateValidation:

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "25/12/2024",        # wrong separator
        "2024-13-01",        # month out of range
        "2024-00-10",        # month zero
        "2024-01-32",        # day out of range
        "20240101",          # missing dashes
        "",                  # empty string
        "yesterday",         # natural language
    ])
    def test_invalid_date_rerenders_form_with_200(self, auth_client, bad_date):
        tc, _, _ = auth_client
        payload = _valid_payload(date=bad_date)
        response = tc.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            f"Invalid date {bad_date!r} must re-render the form (200)"
        )

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "25/12/2024",
        "",
    ])
    def test_invalid_date_shows_error_message(self, auth_client, bad_date):
        tc, _, _ = auth_client
        payload = _valid_payload(date=bad_date)
        response = tc.post("/expenses/add", data=payload)
        assert b"valid date" in response.data or b"Please enter" in response.data, (
            f"An error message about a valid date must appear for date={bad_date!r}"
        )

    def test_invalid_date_does_not_insert_row(self, auth_client, app):
        tc, user_id, _ = auth_client
        unique_desc = f"bad-date-{uuid.uuid4().hex[:8]}"
        tc.post("/expenses/add", data=_valid_payload(date="not-a-date", description=unique_desc))

        with app.app_context():
            db = get_db()
            try:
                row = db.execute(
                    "SELECT id FROM expenses WHERE user_id = ? AND description = ?",
                    (user_id, unique_desc),
                ).fetchone()
            finally:
                db.close()

        assert row is None, "No DB row must be inserted when date validation fails"


# ---------------------------------------------------------------------------
# 8. Validation errors — category
# ---------------------------------------------------------------------------

class TestCategoryValidation:

    @pytest.mark.parametrize("bad_category", [
        "",
        "food",           # wrong case
        "FOOD",           # all caps
        "InvalidCat",     # not in allowed list
        "Groceries",      # plausible but not in list
        "Salary",         # not in list
        "<script>xss",    # injection attempt
    ])
    def test_invalid_category_rerenders_form_with_200(self, auth_client, bad_category):
        tc, _, _ = auth_client
        payload = _valid_payload(category=bad_category)
        response = tc.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            f"Invalid category {bad_category!r} must re-render the form (200)"
        )

    @pytest.mark.parametrize("bad_category", [
        "", "InvalidCat", "food",
    ])
    def test_invalid_category_shows_error_message(self, auth_client, bad_category):
        tc, _, _ = auth_client
        payload = _valid_payload(category=bad_category)
        response = tc.post("/expenses/add", data=payload)
        assert b"valid category" in response.data or b"Please select" in response.data, (
            f"An error about a valid category must appear for category={bad_category!r}"
        )

    def test_invalid_category_does_not_insert_row(self, auth_client, app):
        tc, user_id, _ = auth_client
        unique_desc = f"bad-cat-{uuid.uuid4().hex[:8]}"
        tc.post("/expenses/add", data=_valid_payload(category="Nonsense", description=unique_desc))

        with app.app_context():
            db = get_db()
            try:
                row = db.execute(
                    "SELECT id FROM expenses WHERE user_id = ? AND description = ?",
                    (user_id, unique_desc),
                ).fetchone()
            finally:
                db.close()

        assert row is None, "No DB row must be inserted when category validation fails"


# ---------------------------------------------------------------------------
# 9. Field repopulation on validation error
# ---------------------------------------------------------------------------

class TestFieldRepopulation:

    def test_amount_repopulated_after_invalid_date(self, auth_client):
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload(
            amount="77.77", date="bad-date"
        ))
        assert b"77.77" in response.data, (
            "Submitted amount must be echoed back when date validation fails"
        )

    def test_category_repopulated_after_invalid_amount(self, auth_client):
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload(
            amount="0", category="Health"
        ))
        # The Health option must appear selected in the re-rendered form
        assert b"Health" in response.data, (
            "Submitted category must be echoed back when amount validation fails"
        )

    def test_date_repopulated_after_invalid_amount(self, auth_client):
        tc, _, _ = auth_client
        submitted_date = "2025-11-20"
        response = tc.post("/expenses/add", data=_valid_payload(
            amount="0", date=submitted_date
        ))
        assert submitted_date.encode() in response.data, (
            "Submitted date must be echoed back when amount validation fails"
        )

    def test_description_repopulated_after_invalid_category(self, auth_client):
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload(
            category="BadCat", description="My description stays"
        ))
        assert b"My description stays" in response.data, (
            "Submitted description must be echoed back when category validation fails"
        )

    def test_amount_repopulated_after_invalid_category(self, auth_client):
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload(
            amount="33.33", category=""
        ))
        assert b"33.33" in response.data, (
            "Submitted amount must be echoed back when category validation fails"
        )


# ---------------------------------------------------------------------------
# 10. SQL parameterisation (structural check on source file)
# ---------------------------------------------------------------------------

class TestSQLParameterisation:

    def test_insert_statement_uses_placeholders_not_string_format(self, app):
        """
        Read app.py and verify the INSERT INTO expenses statement uses ?
        placeholders rather than %-formatting or f-string interpolation.
        This is a structural safety check, not an execution test.
        """
        import os
        app_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "app.py"
        )
        with open(app_path, encoding="utf-8") as fh:
            source = fh.read()

        # Find the INSERT statement targeting the expenses table
        insert_pattern = re.compile(
            r'INSERT\s+INTO\s+expenses.*?(?=\n\s*\)|\Z)',
            re.IGNORECASE | re.DOTALL,
        )
        matches = insert_pattern.findall(source)
        assert matches, "An INSERT INTO expenses statement must exist in app.py"

        for match in matches:
            assert "%" not in match or "VALUES" not in match or "?" in match, (
                "INSERT INTO expenses must not use %-style string formatting"
            )
            # Must contain ? placeholders, not f-string braces around column names
            assert "{" not in match, (
                "INSERT INTO expenses must not use f-string / .format() interpolation"
            )
            assert "?" in match, (
                "INSERT INTO expenses must use ? parameterised placeholders"
            )

    def test_no_fstring_sql_in_add_expense_route(self, app):
        """Verify the add_expense route body contains no f-string SQL construction."""
        import os
        app_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "app.py"
        )
        with open(app_path, encoding="utf-8") as fh:
            source = fh.read()

        # Look for f-string literals that contain SQL keywords — a clear red flag
        fstring_sql = re.findall(r'f["\'].*?(?:SELECT|INSERT|UPDATE|DELETE).*?["\']', source, re.IGNORECASE)
        assert not fstring_sql, (
            f"SQL queries must not be built with f-strings. Found: {fstring_sql}"
        )


# ---------------------------------------------------------------------------
# 11. No hex colour values in template markup
# ---------------------------------------------------------------------------

class TestNoHexColoursInTemplate:

    def test_add_expense_template_has_no_hex_colour_literals(self, app):
        """
        The template must use CSS variables / class names only —
        no raw hex colour values (#rrggbb or #rgb) in the markup.
        """
        import os
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "templates", "add_expense.html"
        )
        with open(template_path, encoding="utf-8") as fh:
            markup = fh.read()

        # Match standalone hex colour values: #FFF, #FFFFFF, #fff, #ffffff etc.
        # Exclude CSS variable references like var(--some-name) which may contain words.
        hex_colours = re.findall(r'(?<![a-zA-Z0-9_-])#[0-9a-fA-F]{3,6}\b', markup)
        assert not hex_colours, (
            f"Template must not contain hex colour literals. Found: {hex_colours}"
        )


# ---------------------------------------------------------------------------
# 12. Cross-user data isolation
# ---------------------------------------------------------------------------

class TestCrossUserIsolation:

    def test_expense_not_attributed_to_other_user(self, auth_client, app):
        """Expense row's user_id must match only the logged-in user, not any other."""
        tc, user_id, _ = auth_client

        # Create a second isolated user in the DB
        other_email = _unique_email()
        with flask_app.app_context():
            db = get_db()
            try:
                cur = db.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    ("Other User", other_email, generate_password_hash("OtherPass1")),
                )
                other_id = cur.lastrowid
                db.commit()
            finally:
                db.close()

        try:
            unique_desc = f"isolation-{uuid.uuid4().hex[:8]}"
            tc.post("/expenses/add", data=_valid_payload(description=unique_desc))

            with app.app_context():
                db = get_db()
                try:
                    row = db.execute(
                        "SELECT user_id FROM expenses WHERE description = ?",
                        (unique_desc,),
                    ).fetchone()
                finally:
                    db.close()

            assert row is not None, "Expense must be inserted"
            assert row["user_id"] == user_id, (
                "Expense user_id must belong to the logged-in user, not any other"
            )
            assert row["user_id"] != other_id, (
                "Expense must not be attributed to a different user"
            )
        finally:
            # Clean up the extra user
            with flask_app.app_context():
                db = get_db()
                try:
                    db.execute("DELETE FROM expenses WHERE user_id = ?", (other_id,))
                    db.execute("DELETE FROM users WHERE id = ?", (other_id,))
                    db.commit()
                finally:
                    db.close()


# ---------------------------------------------------------------------------
# 13. Parametrized all-valid-categories happy-path
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
])
def test_each_valid_category_accepted_by_server(auth_client, app, category):
    """Every category in the allowed list must be accepted and persisted."""
    tc, user_id, _ = auth_client
    unique_desc = f"cat-test-{category.lower()}-{uuid.uuid4().hex[:6]}"
    response = tc.post("/expenses/add", data=_valid_payload(
        category=category, description=unique_desc
    ))
    assert response.status_code == 302, (
        f"Category '{category}' must be accepted and produce a 302 redirect"
    )

    with flask_app.app_context():
        db = get_db()
        try:
            row = db.execute(
                "SELECT category FROM expenses WHERE user_id = ? AND description = ?",
                (user_id, unique_desc),
            ).fetchone()
        finally:
            db.close()

    assert row is not None, f"Expense with category '{category}' must be persisted"
    assert row["category"] == category, (
        f"Stored category must equal '{category}'"
    )


# ---------------------------------------------------------------------------
# 14. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_very_large_valid_amount_is_accepted(self, auth_client, app):
        tc, user_id, _ = auth_client
        unique_desc = f"large-amt-{uuid.uuid4().hex[:8]}"
        response = tc.post("/expenses/add", data=_valid_payload(
            amount="999999.99", description=unique_desc
        ))
        assert response.status_code == 302, (
            "A large but valid amount must be accepted"
        )

    def test_sql_injection_in_description_is_safe(self, auth_client, app):
        """Parameterised queries must safely store injection payloads as plain text."""
        tc, user_id, _ = auth_client
        injection_desc = "'; DROP TABLE expenses; --"
        response = tc.post("/expenses/add", data=_valid_payload(description=injection_desc))
        # Must redirect (not crash)
        assert response.status_code == 302, (
            "SQL injection payload in description must not crash the server"
        )

        with app.app_context():
            db = get_db()
            try:
                # The expenses table must still exist and contain our row
                row = db.execute(
                    "SELECT description FROM expenses WHERE user_id = ? AND description = ?",
                    (user_id, injection_desc),
                ).fetchone()
                # Also confirm the table itself survived
                tables = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'"
                ).fetchone()
            finally:
                db.close()

        assert tables is not None, "expenses table must still exist after injection attempt"
        assert row is not None, "Injection payload must be stored as literal text, not executed"

    def test_minimum_valid_amount_accepted(self, auth_client):
        """0.01 is the minimum valid amount per the spec (min="0.01")."""
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload(amount="0.01"))
        assert response.status_code == 302, (
            "Amount of 0.01 (the minimum) must be accepted"
        )

    def test_whitespace_only_description_does_not_break_submission(self, auth_client):
        """Whitespace-only description is optional — submission must still succeed."""
        tc, _, _ = auth_client
        response = tc.post("/expenses/add", data=_valid_payload(description="   "))
        assert response.status_code == 302, (
            "Whitespace-only description must not cause a validation failure"
        )
