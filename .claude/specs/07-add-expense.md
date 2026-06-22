# Spec: Add Expense

## Overview
This feature implements the Add Expense form, allowing logged-in users to record a new expense with an amount, category, date, and optional description. The existing stub `GET /expenses/add` route is replaced with a full GET/POST route that renders a form on GET and inserts a row into the `expenses` table on POST. After a successful submission the user is redirected to their profile page so they can immediately see the new expense in the transaction list.

## Depends on
- Step 01: Database setup (`expenses` table must exist)
- Step 02: Registration (user accounts must exist)
- Step 03: Login + Logout (session must be active to access the route)
- Step 04: Profile page design (redirect target after successful add)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense, then redirect to `/profile` — logged-in only

## Database changes
No database changes. The `expenses` table already exists with the required columns: `user_id`, `amount`, `category`, `date`, `description`.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Form with `method="post"` and `action="/expenses/add"`
  - Fields:
    - `amount` — `<input type="number" step="0.01" min="0.01">` (required)
    - `category` — `<select>` with options: Food, Transport, Bills, Health, Entertainment, Shopping, Other (required)
    - `date` — `<input type="date">` pre-populated with today's date (required)
    - `description` — `<input type="text">` (optional)
  - Submit button labelled "Add Expense"
  - If the form is re-rendered after a validation error, repopulate all fields with the submitted values and show the error message above the form

## Files to change
- `app.py` — replace the stub `add_expense` route with a full GET/POST implementation:
  - `GET`: render `add_expense.html` with today's date pre-populated
  - `POST`: read `amount`, `category`, `date`, `description` from `request.form`
    - Validate that `amount` is a positive number
    - Validate that `date` is a valid `YYYY-MM-DD` string (reuse `is_valid_date`)
    - Validate that `category` is one of the seven allowed values
    - On any validation failure, re-render the form with the submitted values and an error message
    - On success, insert the expense with a parameterised `INSERT INTO expenses` query and redirect to `/profile`
  - Both GET and POST must call `login_required()` and return the guard if not authenticated

## Files to create
- `templates/add_expense.html` — the add-expense form template (see Templates section)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- The `amount` field must use `type="number"` with `step="0.01"` and `min="0.01"`
- The `date` field must use `type="date"` and default to today's date
- Category must be validated server-side against the fixed allowed list, not just relied on client-side
- The POST route must redirect to `/profile` on success (never re-render the form after a successful insert)
- Do not use `float()` directly on untrusted input without catching `ValueError`

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders a form with amount, category, date, and description fields
- [ ] The date field is pre-populated with today's date on GET
- [ ] Submitting valid data inserts a row into the `expenses` table and redirects to `/profile`
- [ ] The new expense appears in the transaction list on the profile page after redirect
- [ ] Submitting with a missing or zero amount re-renders the form with an error message and all other fields repopulated
- [ ] Submitting with an invalid date re-renders the form with an error message
- [ ] Submitting with an invalid category re-renders the form with an error message
- [ ] All SQL queries use parameterised placeholders — no string interpolation
- [ ] No hex colour values appear in the template markup — only CSS variables or class names
