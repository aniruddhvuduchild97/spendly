# Spec: Registration

## Overview
Implement user registration and login so visitors can create a Spendly account and sign in. This step wires up the POST handlers for the forms that already exist in `register.html` and `login.html`, adds Flask session support, and makes the navbar reflect the logged-in state. After registering or signing in, the user is redirected to a `/dashboard` stub that will be fully built in a later step.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`, `init_db()`, `seed_db()` must all be working)

## Routes
- `GET  /register` — render registration form — public *(already exists, no change needed)*
- `POST /register` — validate and insert new user, set session, redirect to `/dashboard` — public
- `GET  /login` — render login form — public *(already exists, no change needed)*
- `POST /login` — verify credentials, set session, redirect to `/dashboard` — public
- `GET  /dashboard` — placeholder stub (`"Dashboard — coming in a later step"`) — logged-in

## Database changes
No database changes. The `users` table created in Step 01 has all required columns:
`id`, `name`, `email`, `password_hash`, `created_at`.

## Templates
- **Modify:** `templates/base.html` — make nav links conditional:
  - Logged-out: show "Sign in" → `/login` and "Get started" → `/register`
  - Logged-in: show "Dashboard" → `/dashboard` and "Log out" → `/logout`
  - Use `session.get('user_id')` to detect state

## Files to change
- `app.py` — add imports, `secret_key`, POST handlers for `/register` and `/login`, `/dashboard` stub
- `templates/base.html` — conditional navbar links

## Files to create
None. `register.html` and `login.html` already exist with the correct markup and `{% if error %}` blocks.

## New dependencies
No new dependencies. `werkzeug.security` (already in requirements) and `flask.session` (part of Flask) cover everything needed.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use string formatting in SQL
- Hash passwords with `werkzeug.security.generate_password_hash`; verify with `check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Set `app.secret_key` to a hard-coded dev string (e.g. `"spendly-dev-secret"`) — acceptable for this student project
- Store only `user_id` and `user_name` in the session (not the password hash)
- On duplicate email during registration, re-render `register.html` with `error="An account with that email already exists."`
- On bad credentials at login, re-render `login.html` with `error="Invalid email or password."`
- Minimum password length: 8 characters — validate server-side; re-render form with error if too short
- After successful registration or login, redirect with `redirect(url_for('dashboard'))`
- Do not redirect logged-in users away from `/register` or `/login` — that guard belongs in a later step

## Definition of done
- [ ] Visiting `/register` renders the registration form
- [ ] Submitting the form with a new email creates a user row in the database with a hashed password (confirm via `seed_user` or sqlite3 CLI)
- [ ] After registering, the browser lands on `/dashboard` without an error
- [ ] Submitting the registration form with a duplicate email re-renders the form with an error message
- [ ] Submitting the registration form with a password shorter than 8 characters re-renders the form with an error message
- [ ] Visiting `/login` renders the login form
- [ ] Signing in with valid credentials (e.g. `demo@spendly.com` / `demo123`) lands on `/dashboard`
- [ ] Signing in with a wrong password re-renders the login form with an error message
- [ ] After logging in, the navbar shows "Dashboard" and "Log out" instead of "Sign in" and "Get started"
- [ ] After logging out (navigate to `/logout` manually), the navbar reverts to "Sign in" and "Get started"
