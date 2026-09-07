# HR Servicedesk

A self-hosted HR/IT ticketing portal built with Django — department-based queues, SLA and auto-close automation, a self-service knowledge base, and live dashboards, wrapped in a fully rebrandable glassmorphic UI.

<!-- Optional: replace with a real screenshot of your dashboard -->
<!-- ![Dashboard screenshot](docs/screenshot-dashboard.png) -->

![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-6.1-0C4B33)
![License](https://img.shields.io/badge/license-unspecified-lightgrey)

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Roles & permissions](#roles--permissions)
- [Quick start (local development)](#quick-start-local-development)
- [Configuration](#configuration)
- [Production deployment](#production-deployment)
- [Project structure](#project-structure)
- [Security](#security)
- [License](#license)

## Features

**Ticketing**
- Full ticket lifecycle — Open → In Progress → Resolved → Closed, with priorities (Low/Normal/High/Urgent) and category-based routing to a department
- Threaded replies with internal (staff-only) notes, file attachments, and canned response templates per department
- SLA targets and auto-close rules configurable per department, plus escalation flags
- "Who else is viewing this ticket" live presence indicator
- CSV export of any filtered ticket queue

**Self-service**
- Knowledge base with published/draft articles, scoped so reps can only manage their own department's content
- Ticket submission form with dynamic category lists per department

**Admin & operations**
- Role-based dashboards (Employee / Functional Rep / Admin) with charts for ticket aging, status breakdown, department load, agent workload, and average resolution time
- Fully rebrandable portal — name, logo, background, and theme colors, editable from the admin UI
- User and department management, including pre-provisioning accounts before a person's first login
- Optional inbound-email-to-ticket ingestion via a Celery task (IMAP)
- A read-only REST API mirroring the same access rules as the web UI

**Auth**
- Microsoft Entra ID (Azure AD) single sign-on in production
- A mock Active Directory backend for local development (no real AD/SSO needed to get started)

## Tech stack

- **Backend:** Django, Django REST Framework
- **Async/background jobs:** Celery + Redis (inbound email, SLA/auto-close rules)
- **Database:** SQLite in development, PostgreSQL in production
- **File storage:** local disk in development; S3-compatible storage (e.g. Supabase Storage) in production
- **Frontend:** server-rendered Django templates, vanilla JS, Chart.js — no build step required

## Roles & permissions

| Role | Can do |
|---|---|
| **Employee** | Submit tickets, view their own tickets, browse the knowledge base |
| **Functional Rep** | Everything an Employee can, plus manage tickets for their assigned department(s), reply, reassign, and manage that department's knowledge base articles |
| **Admin** | Everything, plus manage users, departments, SLA/workflow rules, and global portal branding |

## Quick start (local development)

**Prerequisites:** Python 3.10+

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd hr-servicedesk

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example environment file (defaults are fine for local dev)
cp .env.example .env

# 5. Apply migrations
python manage.py migrate

# 6. (Optional) Generate a mock Active Directory roster for local login
python create_mock_ad.py

# 7. Create an admin account
python manage.py createsuperuser

# 8. Run it
python manage.py runserver
```

Open **http://127.0.0.1:8000/**. In development the app authenticates against the generated mock AD roster (or your superuser), so no Microsoft SSO setup is required to try it out. Once logged in, head to **Admin Tools → Portal Branding** and **Admin Tools → Departments** to configure your instance.

## Configuration

All configuration is via environment variables — see [`.env.example`](.env.example) for the full list with descriptions. The essentials:

| Variable | Purpose |
|---|---|
| `DJANGO_DEBUG` | `True` for local dev (SQLite + mock AD), `False` for production |
| `DJANGO_SECRET_KEY` | Required when `DJANGO_DEBUG=False` |
| `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` | Required when `DJANGO_DEBUG=False` |
| `POSTGRES_*` | Required when `DJANGO_DEBUG=False` |
| `MS_TENANT_ID` / `MS_CLIENT_ID` / `MS_CLIENT_SECRET` | Required when `DJANGO_DEBUG=False` — enables Microsoft Entra ID SSO |
| `AWS_STORAGE_BUCKET_NAME` + `AWS_S3_*` | Required when `DJANGO_DEBUG=False` — Django does not serve local media files in production, so attachments/branding need S3-compatible storage |
| `REDIS_CACHE_URL` / `CELERY_BROKER_URL` | Needed for the live presence indicator to work correctly across multiple app workers, and for inbound-email/SLA background jobs |

The app fails fast with a clear error at startup if a required production variable is missing, rather than deploying silently broken.

## Production deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for a generic Linux/Gunicorn/PostgreSQL deployment, or [`RENDER_DEPLOY.md`](RENDER_DEPLOY.md) for a one-click [Render](https://render.com) + Supabase deployment using the included `render.yaml`.

## Project structure

```
config/     Django project settings, URL root, WSGI/ASGI, Celery app
users/      Auth (SSO + mock AD), user/department/branding management, RBAC decorators
tickets/    Ticket model, views, forms, knowledge base, REST API, Celery tasks
templates/  Server-rendered HTML (Django templates)
static/     CSS and other static assets
```

## Security

- Role-based access control enforced centrally via `users/decorators.py`
- File uploads are validated by extension and size on every upload path
- The REST API is read-only and scoped to the same per-role visibility rules as the web UI
- CSV exports are sanitized against formula-injection ("CSV injection")
- Ticket/dashboard data embedded into inline `<script>` blocks is escaped to prevent stored XSS

Found a security issue? Please report it privately rather than opening a public issue.

## License

No license has been specified for this project yet. Add a `LICENSE` file (e.g. MIT, Apache-2.0) before distributing or open-sourcing it.
