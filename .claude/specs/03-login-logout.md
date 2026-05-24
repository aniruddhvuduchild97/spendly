# Spec: Login and Logout

## Overview
Complete the login/logout flow by building a real dashboard page, adding a `login_required` guard to protect authenticated routes, and redirecting already-logged-in users away from public-only pages (`/login`, `/register`). The route handlers for `GET/POST /login` and `GET /logout` were stubbed in Step 02; this step hardens those stubs and makes the post-login destination meaningful.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`, `init_db()`, `seed_db()` must all be working)
- Step 02 — Registration (`/register` POST handler, session variables `user_id` and `user_name` set on sign-up)

## Routes
- `GET  /login`     — if already logged in, redirect to `/dashboard`; otherwise render form — public
- `POST /login`     — already implemented; no change needed
- `GET  /logout`    — already implemented; no change needed
- `GET  /dashboard` — render `dashboard.html` with the logged-in user's name; redirect to `/login` if not authenticated — logged-in

## Database changes
No database changes. All required columns (`id`, `name`, `email`, `password_hash`, `created_at`) exist in the `users` table.

## Templates
- **Create:** `templates/dashboard.html` — logged-in landing page; greets the user by name, shows a placeholder message that expenses will appear here in a later step; extends `base.html`
- **Modify:** `templates/login.html` — no markup change needed; route now handles the already-logged-in redirect before rendering

## Files to change
- `app.py`
  - Add a `login_required` helper (inner function or simple inline check) that redirects to `/login` when `session.get('user_id')` is falsy
  - `GET /login`: add early redirect to `/dashboard` if user is already logged in
  - `GET /register`: add early redirect to `/dashboard` if user is already logged in
  - `GET /dashboard`: replace the placeholder string with `render_template('dashboard.html', name=session['user_name'])` and guard with `login_required`

## Files to create
- `templates/dashboard.html` — extends `base.html`; displays a welcome heading and a "your expenses will appear here" placeholder card

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security` — already in place from Step 02
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Implement `login_required` as a plain helper (e.g. a function that returns a redirect or `None`) — do not use a decorator yet; that refactor belongs in a later step
- Do not import or use `functools.wraps` or `@login_required` decorator pattern
- After redirect, pass `next` query-parameter forwarding only if trivially simple; skip it if it adds complexity

## Definition of done
- [ ] Visiting `/dashboard` while logged out redirects to `/login`
- [ ] Visiting `/dashboard` while logged in renders `dashboard.html` with the user's name in a greeting
- [ ] Visiting `/login` while already logged in redirects to `/dashboard` (no login form shown)
- [ ] Visiting `/register` while already logged in redirects to `/dashboard`
- [ ] Clicking "Log out" in the navbar clears the session and lands on the landing page
- [ ] After logout, the navbar shows "Sign in" and "Get started" (not "Dashboard" / "Log out")
- [ ] The seed user (`demo@spendly.com` / `demo123`) can log in and see the dashboard greeting
