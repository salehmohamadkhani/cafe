# Cafe POS

> Multi-tenant point-of-sale and inventory management system for cafes and restaurants — built for the Iranian market.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

A production-ready POS platform that runs multiple independent cafes from a single deployment. Each tenant gets its own isolated database, provisioned on demand from a master portal.

---

## Features

**Point of sale**
- Table-based ordering with live floor status
- Takeaway and walk-up order flows
- Menu and category management
- Thermal receipt printing

**Inventory**
- Stock tracking tied to menu items
- Multi-warehouse support with pre-production stages
- Automatic deduction as orders are fulfilled

**Multi-tenancy**
- Master portal provisions new tenants with isolated databases
- Per-tenant authentication, dashboard, and settings
- Central oversight across all tenants

**Auth and roles**
- Role-based access: master, admin, cashier
- OTP login over SMS
- Session-backed auth with persistent secret keys

**Localization**
- Jalali (Persian) calendar throughout
- FarazSMS gateway integration for Iranian numbers
- RTL Persian interface

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Flask 3.0, Flask-Login, Flask-RESTful |
| ORM | SQLAlchemy 2.0, Flask-Migrate (Alembic) |
| Database | PostgreSQL (production), SQLite (development) |
| Frontend | Jinja2 templates, vanilla JS, CSS |
| SMS | FarazSMS pattern-based API |
| Dates | jdatetime (Jalali calendar) |
| Serving | Gunicorn behind Nginx |

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ (or SQLite for local development)
- A FarazSMS account for OTP delivery

### Installation

```bash
git clone https://github.com/salehmohamadkhani/cafe.git
cd cafe
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements_production.txt
```

> **Note:** `requirements.txt` is a full development freeze and pulls in
> unrelated heavy packages. Use `requirements_production.txt` for a real
> deployment, or `requirements_minimal.txt` to just get it running.

### Configuration

Set the following environment variables (or place them in a `.env` file):

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session key. Auto-generated into `instance/secret_key` if unset. |
| `DATABASE_URL` | PostgreSQL connection string. Falls back to local SQLite. |
| `FARAZSMS_API_KEY` | FarazSMS API key for OTP delivery |
| `FARAZSMS_PATTERN_CODE` | Approved SMS pattern code |
| `FLASK_ENV` | `development` or `production` |

See [`FARAZSMS_SETUP.md`](FARAZSMS_SETUP.md) and
[`FARAZSMS_PATTERN_GUIDE.md`](FARAZSMS_PATTERN_GUIDE.md) for gateway setup.

### Database setup

```bash
flask db upgrade
python create_master_user.py     # create the master portal account
```

### Running

```bash
# Development
python app.py

# Production
gunicorn -c gunicorn_config.py wsgi:app
```

Deployment notes and the Nginx config live in
[`DEPLOYMENT.md`](DEPLOYMENT.md) and [`nginx_config.conf`](nginx_config.conf).

---

## Project Structure

```
cafe/
├── app.py                  # Application factory and entry point
├── config.py               # Environment-driven configuration
├── auth.py                 # Authentication helpers
├── wsgi.py                 # Production WSGI entry point
├── models/
│   ├── models.py           # Tenant-scoped models
│   └── master_models.py    # Master portal models
├── routes/
│   ├── pos.py              # Point-of-sale flows
│   ├── order.py            # Order lifecycle
│   ├── table.py            # Table and floor management
│   ├── takeaway.py         # Takeaway orders
│   ├── menu.py             # Menu and categories
│   ├── admin.py            # Admin panel
│   ├── dashboard.py        # Reporting
│   ├── master_portal.py    # Cross-tenant administration
│   └── tenant*.py          # Per-tenant auth and dashboards
├── services/
│   ├── inventory_service.py
│   ├── sms_service.py
│   └── tenant_provisioning.py
├── utils/
│   ├── printer.py          # Thermal receipt printing
│   └── helpers.py
├── migrations/             # Alembic migrations
├── templates/              # Jinja2 templates
└── static/                 # CSS, JS, assets
```

---

## License

Released under the [MIT License](LICENSE).

---

<div align="center">
  Built by <a href="https://github.com/salehmohamadkhani">M. Saleh Mohammadkhani</a>
</div>
