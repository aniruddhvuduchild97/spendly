# Spec: Date Filter for Profile Page

## Overview
This feature adds a date range filter to the profile page so users can narrow the transaction history, summary stats, and category breakdown to a specific time window. The filter is submitted as query parameters on the existing `GET /profile` route — no new routes are needed. Stats (total spent, transaction count, top category) and the category breakdown must all recalculate to reflect only the filtered transactions. This step assumes Step 05 (backend connection for profile page) is complete, meaning `/profile` already reads real data from the database.

## Depends on
- Step 01: Database setup (`expenses` table must exist)
- Step 02: Registration (user accounts must be creatable)
- Step 03: Login + Logout (session must be active to view `/profile`)
- Step 04: Profile page design (template structure to modify)
- Step 05: Backend route for profile page (real DB queries must already be in place)

## Routes
- `GET /profile?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — returns the profile page filtered to the given date range — logged-in only

No new routes. The existing `/profile` route is extended to accept optional `start_date` and `end_date` query parameters.

## Database changes
No database changes. The existing `expenses` table has a `date TEXT` column (stored as `YYYY-MM-DD`) that supports range filtering with `WHERE date BETWEEN ? AND ?`.

## Templates
- **Modify:** `templates/profile.html`
  - Add a date filter form above the transaction history table
  - Form uses `method="get"` and `action="/profile"` with two `<input type="date">` fields: `start_date` and `end_date`
  - Pre-populate both inputs with the currently applied filter values so the form reflects what is active
  - Add a "Filter" submit button and a "Clear" link that navigates to `/profile` with no query params
  - Transaction table, stats row, and category breakdown must all update visually when a filter is active

## Files to change
- `app.py` — update the `/profile` route to:
  - Read `start_date` and `end_date` from `request.args` (both optional)
  - Default `start_date` to the first day of the current month and `end_date` to today when neither is supplied
  - Query the `expenses` table with `WHERE user_id = ? AND date BETWEEN ? AND ?` using parameterised queries
  - Recalculate `total_spent`, `transaction_count`, `top_category`, and `categories` from the filtered rows
  - Pass `start_date` and `end_date` back to the template so the form can pre-populate
- `templates/profile.html` — add the date filter form (see Templates section above)

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Date inputs must use `type="date"` (native browser date picker — no third-party libraries)
- The filter form must use `method="get"` so the selected range is bookmarkable via the URL
- If `start_date` is after `end_date`, render the profile page with an error message and no transactions
- `top_category` must be derived dynamically from the filtered result set, not hardcoded
- When no expenses match the filter, show an empty-state message in the transaction table instead of hiding the table entirely

## Definition of done
- [ ] Visiting `/profile` without query params shows expenses defaulting to the current month
- [ ] Submitting the filter form with a valid date range updates the transaction list to show only expenses within that range
- [ ] Total spent, transaction count, and top category all reflect only the filtered transactions
- [ ] Category breakdown rows reflect only the filtered transactions
- [ ] The date inputs are pre-populated with the currently active `start_date` and `end_date` after filtering
- [ ] Clicking "Clear" navigates to `/profile` with no query params and resets to the default view
- [ ] Entering a `start_date` later than `end_date` shows a user-facing error message
- [ ] A date range with no matching expenses shows an empty-state message in the transaction table
- [ ] All SQL queries use parameterised placeholders — no string interpolation
- [ ] No hex colour values appear in the date filter form markup — only CSS variables or class names
