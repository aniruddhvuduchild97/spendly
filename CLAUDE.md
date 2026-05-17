# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server (port 5001)
python app.py

# Run tests
pytest

# Run a single test file
pytest tests/test_foo.py
```
## Project Overview
Spendly is a lightweight personal expense tracker built with Flask and SQLite.

## Architecture
spendly/
├── app.py              # All routes — single file, no blueprints
├── database/
│   └── db.py           # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│   ├── base.html       # Shared layout — all templates must extend this
│   └── *.html          # One template per page
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles
│   │   └── landing.css     # Landing-page-only styles
│   └── js/
│       └── main.js         # Vanilla JS only
└── requirements.txt

**Spendly** is a Flask expense-tracker web app built as a step-by-step student project. The `edit_prompts.txt` file contains the sequential task prompts used to drive development.

### Entry point

`app.py` defines all Flask routes and runs the dev server on port 5001. Routes for expenses (add/edit/delete), logout, and profile are stubs — they return placeholder strings until students implement them in later steps.

### Template system

All pages extend `templates/base.html` (Jinja2 inheritance). `base.html` includes the shared navbar, footer, `static/css/style.css`, and `static/js/main.js`. The landing page additionally loads `static/css/landing.css` via `{% block head %}`.

### Database layer

`database/db.py` is intentionally empty — students implement three functions there:
- `get_db()` — returns a SQLite connection with `row_factory` set and foreign keys enabled
- `init_db()` — creates tables with `CREATE TABLE IF NOT EXISTS`
- `seed_db()` — inserts sample data for development

### Static assets

- `static/css/style.css` — shared styles (navbar, footer, base layout)
- `static/css/landing.css` — landing page-only styles
- `static/js/main.js` — shared JS (students add to this as features are built); landing page modal logic lives inline in `templates/landing.html`
