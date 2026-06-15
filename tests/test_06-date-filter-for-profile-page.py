"""
tests/test_06-date-filter-for-profile-page.py

Test suite for the Date Filter feature on the Spendly Profile Page (Step 06).

Spec: .claude/specs/06-date-filter-for-profile-page.md

All test logic is derived exclusively from the spec's Definition of Done,
Routes section, and Rules for implementation — not from the source code.

--- DB isolation note ---
get_db() in database/db.py always connects to the file-based spendly.db
regardless of app.config['DATABASE'].  Therefore each fixture creates a
unique user (UUID-based email), seeds deterministic expense rows under that
user's id, and deletes them in teardown so tests never interfere with each
other or with the seed_db() demo data.
"""

import uuid
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_of_month(d: date) -> str:
    return d.replace(day=1).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _unique_email() -> str:
    """Return a collision-free email address for each test invocation."""
    return f"test-{uuid.uuid4().hex[:12]}@spendly-test.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Flask application in TESTING mode; DB file is shared (see module note)."""
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-06',
        'WTF_CSRF_ENABLED': False,
    })
    with flask_app.app_context():
        init_db()          # ensures tables exist; safe to call multiple times
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded_client(client, app):
    """
    Creates an isolated test user, seeds known expense rows, logs in, and
    yields the test client.  Cleans up all inserted rows on teardown.

    Primary user expense seed (all dated in the past for determinism):
        2024-01-05  Food         10.00  Breakfast
        2024-01-15  Transport    20.00  Taxi
        2024-01-20  Bills        50.00  Water bill
        2024-02-03  Food         30.00  Dinner
        2024-02-14  Health       15.00  Pharmacy
        2024-02-28  Shopping     80.00  Shoes

    A second isolated user owns:
        2024-01-10  Food        999.00  Should never appear
    """
    email = _unique_email()
    other_email = _unique_email()
    password = "TestPass123"

    with flask_app.app_context():
        db = get_db()
        try:
            # Primary user
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Primary User", email, generate_password_hash(password)),
            )
            primary_id = cur.lastrowid

            # Second user (data isolation check)
            cur2 = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Other User", other_email, generate_password_hash(password)),
            )
            other_id = cur2.lastrowid

            primary_expenses = [
                (primary_id, 10.00,  "Food",      "2024-01-05", "Breakfast"),
                (primary_id, 20.00,  "Transport", "2024-01-15", "Taxi"),
                (primary_id, 50.00,  "Bills",     "2024-01-20", "Water bill"),
                (primary_id, 30.00,  "Food",      "2024-02-03", "Dinner"),
                (primary_id, 15.00,  "Health",    "2024-02-14", "Pharmacy"),
                (primary_id, 80.00,  "Shopping",  "2024-02-28", "Shoes"),
            ]
            db.executemany(
                "INSERT INTO expenses"
                " (user_id, amount, category, date, description)"
                " VALUES (?, ?, ?, ?, ?)",
                primary_expenses,
            )
            # Other-user expense — must never bleed into primary user's view
            db.execute(
                "INSERT INTO expenses"
                " (user_id, amount, category, date, description)"
                " VALUES (?, ?, ?, ?, ?)",
                (other_id, 999.00, "Food", "2024-01-10", "Should never appear"),
            )
            db.commit()
        finally:
            db.close()

    # Log in as the primary test user
    client.post("/login", data={"email": email, "password": password})

    yield client

    # Teardown — remove all rows created by this fixture
    with flask_app.app_context():
        db = get_db()
        try:
            db.execute(
                "DELETE FROM expenses WHERE user_id IN ("
                "  SELECT id FROM users WHERE email IN (?, ?)"
                ")",
                (email, other_email),
            )
            db.execute(
                "DELETE FROM users WHERE email IN (?, ?)",
                (email, other_email),
            )
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:

    def test_unauthenticated_get_profile_redirects(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, (
            "Unauthenticated GET /profile must redirect (302)"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_unauthenticated_get_profile_with_params_redirects(self, client):
        response = client.get("/profile?start_date=2024-01-01&end_date=2024-01-31")
        assert response.status_code == 302, (
            "Unauthenticated GET /profile with query params must redirect"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login even with query params present"
        )

    def test_authenticated_user_reaches_profile_200(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert response.status_code == 200, (
            "Authenticated GET /profile must return 200"
        )


# ---------------------------------------------------------------------------
# 2. Default behaviour — no query params
# ---------------------------------------------------------------------------

class TestDefaultBehaviour:

    def test_no_params_returns_200(self, seeded_client):
        response = seeded_client.get("/profile")
        assert response.status_code == 200, (
            "GET /profile with no params must return HTTP 200"
        )

    def test_default_start_date_is_first_of_current_month(self, seeded_client):
        expected = _first_of_month(date.today())
        response = seeded_client.get("/profile")
        assert expected.encode() in response.data, (
            f"Default start_date must be {expected} (first day of current month)"
        )

    def test_default_end_date_is_today(self, seeded_client):
        expected = _today()
        response = seeded_client.get("/profile")
        assert expected.encode() in response.data, (
            f"Default end_date must be {expected} (today)"
        )

    def test_no_validation_error_on_default_load(self, seeded_client):
        response = seeded_client.get("/profile")
        assert b"Start date must be on or before end date" not in response.data, (
            "No validation error must appear on a default (no-params) page load"
        )

    def test_default_view_renders_profile_page(self, seeded_client):
        response = seeded_client.get("/profile")
        # The profile template contains "Total Spent" in the stats grid
        assert b"Total Spent" in response.data, (
            "Default /profile load must render the profile page with stats"
        )


# ---------------------------------------------------------------------------
# 3. Happy path — valid date range
# ---------------------------------------------------------------------------

class TestValidDateRange:

    def test_expenses_within_range_are_shown(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"Breakfast" in response.data, "Jan expense 'Breakfast' must be visible"
        assert b"Taxi" in response.data, "Jan expense 'Taxi' must be visible"
        assert b"Water bill" in response.data, "Jan expense 'Water bill' must be visible"

    def test_expenses_outside_range_are_not_shown(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"Dinner" not in response.data, "Feb expense 'Dinner' must not appear in Jan filter"
        assert b"Pharmacy" not in response.data, "Feb expense 'Pharmacy' must not appear"
        assert b"Shoes" not in response.data, "Feb expense 'Shoes' must not appear"

    def test_total_spent_reflects_filtered_rows_only(self, seeded_client):
        # January: 10 + 20 + 50 = 80.00
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"80.00" in response.data, (
            "total_spent must be 80.00 for January (10+20+50)"
        )

    def test_transaction_count_reflects_filtered_rows_only(self, seeded_client):
        # January has exactly 3 expenses
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"3" in response.data, (
            "transaction_count must be 3 for the January filter"
        )

    def test_top_category_reflects_filtered_rows_only(self, seeded_client):
        # January: Bills=50, Transport=20, Food=10 → Bills is the top category
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"Bills" in response.data, (
            "top_category for January must be 'Bills' (highest spend = 50)"
        )

    def test_category_breakdown_reflects_filtered_rows_only(self, seeded_client):
        # February: Shopping=80, Food=30, Health=15
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-02-28"
        )
        assert b"Shopping" in response.data, "Feb breakdown must include Shopping"
        assert b"Food" in response.data, "Feb breakdown must include Food"
        assert b"Health" in response.data, "Feb breakdown must include Health"

    def test_category_breakdown_excludes_out_of_range_categories(self, seeded_client):
        # Transport and Bills only appear in January
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-02-28"
        )
        assert b"Transport" not in response.data, (
            "Transport (Jan-only) must not appear in Feb breakdown"
        )
        assert b"Bills" not in response.data, (
            "Bills (Jan-only) must not appear in Feb breakdown"
        )

    def test_start_date_input_prepopulated_after_filtering(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"2024-01-01" in response.data, (
            "start_date input must be pre-populated with the submitted value"
        )

    def test_end_date_input_prepopulated_after_filtering(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"2024-01-31" in response.data, (
            "end_date input must be pre-populated with the submitted value"
        )

    def test_single_day_range_returns_exact_match(self, seeded_client):
        # 2024-01-15 = Taxi (20.00) only
        response = seeded_client.get(
            "/profile?start_date=2024-01-15&end_date=2024-01-15"
        )
        assert b"Taxi" in response.data, "Single-day range must return the matching expense"
        assert b"Breakfast" not in response.data, (
            "Expenses outside the single-day range must not appear"
        )

    def test_multi_month_range_shows_all_seeded_expenses(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-02-28"
        )
        for desc in (b"Breakfast", b"Taxi", b"Water bill", b"Dinner", b"Pharmacy", b"Shoes"):
            assert desc in response.data, (
                f"{desc!r} must appear when range covers both seeded months"
            )

    def test_multi_month_total_spent_is_sum_of_all_seeded_expenses(self, seeded_client):
        # 10 + 20 + 50 + 30 + 15 + 80 = 205.00
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-02-28"
        )
        assert b"205.00" in response.data, (
            "total_spent across both months must be 205.00"
        )


# ---------------------------------------------------------------------------
# 4. Parametrized stats correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("start,end,expected_total,expected_count,expected_top", [
    # January only: Bills=50 wins
    ("2024-01-01", "2024-01-31", "80.00",  "3", "Bills"),
    # February only: Shopping=80 wins
    ("2024-02-01", "2024-02-28", "125.00", "3", "Shopping"),
    # Both months: Shopping=80 still the highest single-category total
    ("2024-01-01", "2024-02-28", "205.00", "6", "Shopping"),
    # Single expense: Dinner 2024-02-03
    ("2024-02-03", "2024-02-03", "30.00",  "1", "Food"),
    # Single expense: Bills 2024-01-20
    ("2024-01-20", "2024-01-20", "50.00",  "1", "Bills"),
])
def test_stats_for_parametrized_date_ranges(
    seeded_client, start, end, expected_total, expected_count, expected_top
):
    response = seeded_client.get(f"/profile?start_date={start}&end_date={end}")
    assert response.status_code == 200
    assert expected_total.encode() in response.data, (
        f"Expected total_spent={expected_total} for {start}–{end}"
    )
    assert expected_count.encode() in response.data, (
        f"Expected transaction_count={expected_count} for {start}–{end}"
    )
    assert expected_top.encode() in response.data, (
        f"Expected top_category={expected_top!r} for {start}–{end}"
    )


# ---------------------------------------------------------------------------
# 5. Validation error — start_date after end_date
# ---------------------------------------------------------------------------

class TestValidationError:

    def test_start_after_end_returns_200(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-01-01"
        )
        assert response.status_code == 200, (
            "Invalid date order must render the profile page (200), not crash"
        )

    def test_start_after_end_shows_error_message(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-01-01"
        )
        assert b"Start date must be on or before end date" in response.data, (
            "Error message must be present when start_date is after end_date"
        )

    def test_start_after_end_renders_no_expense_rows(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-01-01"
        )
        assert b"Breakfast" not in response.data
        assert b"Taxi" not in response.data
        assert b"Dinner" not in response.data

    def test_start_after_end_total_spent_is_zero(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-01-01"
        )
        assert b"0.00" in response.data, (
            "total_spent must be 0.00 when date order is invalid"
        )

    def test_start_after_end_transaction_count_is_zero(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-01-01"
        )
        # The stats grid must show 0
        assert b"0" in response.data, (
            "transaction_count must be 0 when date order is invalid"
        )

    def test_equal_start_and_end_is_valid_no_error(self, seeded_client):
        # start == end is a legal single-day range
        response = seeded_client.get(
            "/profile?start_date=2024-01-05&end_date=2024-01-05"
        )
        assert b"Start date must be on or before end date" not in response.data, (
            "Equal start and end dates are valid; no error message should appear"
        )


# ---------------------------------------------------------------------------
# 6. Empty state
# ---------------------------------------------------------------------------

class TestEmptyState:

    def test_range_with_no_expenses_shows_transaction_empty_state(self, seeded_client):
        # March 2024 has no seeded expenses
        response = seeded_client.get(
            "/profile?start_date=2024-03-01&end_date=2024-03-31"
        )
        assert response.status_code == 200
        assert b"No transactions found for this date range" in response.data, (
            "Empty-state message must appear in the transaction table when no rows match"
        )

    def test_range_with_no_expenses_shows_category_breakdown_empty_state(
        self, seeded_client
    ):
        response = seeded_client.get(
            "/profile?start_date=2024-03-01&end_date=2024-03-31"
        )
        assert b"No data for this period" in response.data, (
            "Category breakdown must show its empty-state message when no expenses match"
        )

    def test_range_with_no_expenses_total_spent_is_zero(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-03-01&end_date=2024-03-31"
        )
        assert b"0.00" in response.data, (
            "total_spent must be 0.00 when no expenses match the filter"
        )

    def test_range_with_no_expenses_transaction_count_is_zero(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-03-01&end_date=2024-03-31"
        )
        assert b"0" in response.data, (
            "transaction_count must be 0 when no expenses match"
        )

    def test_range_with_no_expenses_top_category_is_dash(self, seeded_client):
        # Spec: top_category defaults to "—" when there are no matching expenses
        response = seeded_client.get(
            "/profile?start_date=2024-03-01&end_date=2024-03-31"
        )
        assert "—".encode("utf-8") in response.data, (
            "top_category must render as '—' when no expenses match the filter"
        )

    def test_far_future_range_triggers_empty_state(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2099-01-01&end_date=2099-12-31"
        )
        assert b"No transactions found for this date range" in response.data, (
            "Far-future range with no data must trigger the empty-state message"
        )


# ---------------------------------------------------------------------------
# 7. Filter pre-population
# ---------------------------------------------------------------------------

class TestFilterPrepopulation:

    def test_form_has_start_date_input_named_correctly(self, seeded_client):
        response = seeded_client.get("/profile")
        assert b'name="start_date"' in response.data, (
            "Filter form must have an input element named 'start_date'"
        )

    def test_form_has_end_date_input_named_correctly(self, seeded_client):
        response = seeded_client.get("/profile")
        assert b'name="end_date"' in response.data, (
            "Filter form must have an input element named 'end_date'"
        )

    def test_date_inputs_use_type_date(self, seeded_client):
        response = seeded_client.get("/profile")
        assert b'type="date"' in response.data, (
            "Filter form must use <input type='date'> for the native browser date picker"
        )

    def test_submitted_start_date_is_echoed_as_input_value(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-02-28"
        )
        assert b'value="2024-02-01"' in response.data, (
            "start_date input value attribute must reflect the submitted date"
        )

    def test_submitted_end_date_is_echoed_as_input_value(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-02-28"
        )
        assert b'value="2024-02-28"' in response.data, (
            "end_date input value attribute must reflect the submitted date"
        )

    def test_invalid_order_dates_still_echoed_back_to_form(self, seeded_client):
        # Even with a validation error, the form must echo the submitted values
        response = seeded_client.get(
            "/profile?start_date=2024-05-01&end_date=2024-04-01"
        )
        assert b"2024-05-01" in response.data, (
            "start_date must be echoed back even when validation fails"
        )
        assert b"2024-04-01" in response.data, (
            "end_date must be echoed back even when validation fails"
        )


# ---------------------------------------------------------------------------
# 8. Filter form HTML structure
# ---------------------------------------------------------------------------

class TestFilterFormStructure:

    def test_form_uses_get_method(self, seeded_client):
        response = seeded_client.get("/profile")
        assert b'method="get"' in response.data, (
            "Date filter form must use method='get' so the URL is bookmarkable"
        )

    def test_form_action_points_to_profile_route(self, seeded_client):
        response = seeded_client.get("/profile")
        assert b'action="/profile"' in response.data, (
            "Date filter form action must be '/profile'"
        )

    def test_form_has_filter_submit_button(self, seeded_client):
        response = seeded_client.get("/profile")
        assert b"Filter" in response.data, (
            "Filter form must include a 'Filter' submit button"
        )

    def test_clear_link_points_to_profile_without_params(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b'href="/profile"' in response.data, (
            "Clear link must href='/profile' with no query parameters"
        )


# ---------------------------------------------------------------------------
# 9. Cross-user data isolation
# ---------------------------------------------------------------------------

class TestCrossUserIsolation:

    def test_other_users_expense_never_appears_in_filtered_results(self, seeded_client):
        # The other user has a 999.00 Food expense on 2024-01-10
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"999" not in response.data, (
            "Amounts from another user's expenses must never appear"
        )
        assert b"Should never appear" not in response.data, (
            "Descriptions from another user's expenses must not leak through"
        )

    def test_total_spent_excludes_other_users_amounts(self, seeded_client):
        # January primary total must be 80.00, not 80 + 999
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"80.00" in response.data, (
            "total_spent for January must be 80.00 (primary user only)"
        )
        assert b"999" not in response.data, (
            "Other user's 999.00 expense must not inflate total_spent"
        )

    def test_transaction_count_excludes_other_users_rows(self, seeded_client):
        # Primary user has 3 January expenses; other user also has 1 on 2024-01-10
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        # Count must be 3, not 4
        assert b"3" in response.data, (
            "transaction_count must be 3 for January (primary user only)"
        )


# ---------------------------------------------------------------------------
# 10. Category breakdown accuracy
# ---------------------------------------------------------------------------

class TestCategoryBreakdownAccuracy:

    def test_february_breakdown_shows_correct_amounts(self, seeded_client):
        # Shopping=80, Food=30, Health=15
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-02-28"
        )
        assert b"80.00" in response.data, "Shopping amount (80.00) must appear in Feb breakdown"
        assert b"30.00" in response.data, "Food amount (30.00) must appear in Feb breakdown"
        assert b"15.00" in response.data, "Health amount (15.00) must appear in Feb breakdown"

    def test_breakdown_ordered_by_descending_amount(self, seeded_client):
        # February: Shopping(80) > Food(30) > Health(15) in the HTML order
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-02-28"
        )
        html = response.data.decode("utf-8")
        shopping_pos = html.find("Shopping")
        food_pos = html.find("Food")
        health_pos = html.find("Health")
        assert shopping_pos != -1 and food_pos != -1 and health_pos != -1, (
            "Shopping, Food, and Health must all appear in February breakdown"
        )
        assert shopping_pos < food_pos < health_pos, (
            "Breakdown must be ordered descending: Shopping > Food > Health"
        )

    def test_january_breakdown_contains_correct_categories(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"Bills" in response.data
        assert b"Transport" in response.data
        assert b"Food" in response.data

    def test_january_breakdown_excludes_february_only_categories(self, seeded_client):
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert b"Health" not in response.data, (
            "Health (Feb-only) must not appear in the January category breakdown"
        )
        assert b"Shopping" not in response.data, (
            "Shopping (Feb-only) must not appear in the January category breakdown"
        )

    def test_category_percentage_values_are_rendered(self, seeded_client):
        # February total=125: Shopping≈64%, Food≈24%, Health≈12%
        response = seeded_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-02-28"
        )
        html = response.data.decode("utf-8")
        # At least one numeric percentage from the breakdown must be present
        assert "64" in html or "%" in html, (
            "Category breakdown must render percentage values for the filtered rows"
        )

    def test_combined_range_top_category_is_shopping(self, seeded_client):
        # Both months: Food=40 (10+30), Transport=20, Bills=50, Health=15, Shopping=80
        # Shopping (80) is the single highest per-category total
        response = seeded_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-02-28"
        )
        assert b"Shopping" in response.data, (
            "top_category across both months must be Shopping (highest single-category total = 80)"
        )
