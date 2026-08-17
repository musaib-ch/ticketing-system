# Production deployment guide

This project has two supported modes:

- **Development:** `DJANGO_DEBUG=True`, SQLite, and `mock_ad.xlsx` authentication.
- **Production:** `DJANGO_DEBUG=False`, PostgreSQL, HTTPS, and Microsoft Entra ID SSO only.

Do not copy `db.sqlite3`, `mock_ad.xlsx`, `.env`, `media/`, or the local `venv/` to source control.

## 1. Prepare the server

The commands below assume Ubuntu/Debian and a Linux service account named `ticketing`.

```bash
sudo apt update
sudo apt install python3 python3-venv postgresql nginx
sudo useradd --system --create-home --shell /usr/sbin/nologin ticketing
sudo mkdir -p /srv/ticketing
sudo chown ticketing:ticketing /srv/ticketing
```

Copy or clone the application into `/srv/ticketing/app`. Create a virtual environment and install the production requirements:

```bash
cd /srv/ticketing/app
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-production.txt
```

## 2. Create PostgreSQL database and account

```bash
sudo -u postgres psql
```

```sql
CREATE USER ticketing_app WITH PASSWORD 'use-a-long-unique-password';
CREATE DATABASE ticketing OWNER ticketing_app;
\q
```

Use a managed PostgreSQL service if preferred. Enforce TLS and use its host, port, and CA requirements.

## 3. Configure environment variables

Copy `.env.example` to a protected server-only file such as `/etc/ticketing.env`, then set at least:

```ini
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<generate-a-long-random-secret>
DJANGO_ALLOWED_HOSTS=tickets.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://tickets.example.com
SITE_URL=https://tickets.example.com
POSTGRES_DB=ticketing
POSTGRES_USER=ticketing_app
POSTGRES_PASSWORD=<database-password>
POSTGRES_HOST=<database-host>
POSTGRES_PORT=5432
POSTGRES_SSLMODE=require
MS_TENANT_ID=<entra-tenant-id>
MS_CLIENT_ID=<entra-application-client-id>
MS_CLIENT_SECRET=<entra-client-secret>
DEFAULT_FROM_EMAIL=no-reply@example.com
EMAIL_HOST=<smtp-host>
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-password>
```

Lock it down:

```bash
sudo chown ticketing:ticketing /etc/ticketing.env
sudo chmod 600 /etc/ticketing.env
```

## 4. Configure Microsoft Entra ID

In Entra ID, create an App Registration for this portal.

1. Add the web redirect URI: `https://tickets.example.com/manage/auth/microsoft/callback/`.
2. Create a client secret and place its value in `MS_CLIENT_SECRET`.
3. Record the Directory (tenant) ID and Application (client) ID.
4. Restrict sign-in to the organisation’s tenant and assign users/groups as required.

Production hides Excel/password login and enables only the Microsoft sign-in button. The callback checks OAuth state and validates the signed Entra ID token.

## 5. Migrate schema and optional existing SQLite data

Always back up both source and destination databases before transferring data.

### Fresh production database

```bash
cd /srv/ticketing/app
set -a; . /etc/ticketing.env; set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
```

### Move development SQLite records to PostgreSQL

On a safe copy of the development project, export data while SQLite settings are active:

```bash
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.Permission --indent 2 > production-data.json
```

Copy `production-data.json` and the contents of `media/` to the server. After configuring PostgreSQL, migrate first and then import:

```bash
set -a; . /etc/ticketing.env; set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py loaddata production-data.json
.venv/bin/python manage.py collectstatic --noinput
```

If PostgreSQL reports a duplicate primary-key error after an import, reset sequences:

```bash
.venv/bin/python manage.py sqlsequencereset users tickets | sudo -u postgres psql ticketing
```

Verify: log in through Entra ID, create a test ticket, upload an attachment, and confirm email delivery.

The production requirements file installs `psycopg[binary]`, the PostgreSQL driver. It is intentionally not required for local SQLite development.

## 6. Run Gunicorn with systemd

Create `/etc/systemd/system/ticketing.service`:

```ini
[Unit]
Description=Ticketing Django application
After=network.target

[Service]
User=ticketing
Group=ticketing
WorkingDirectory=/srv/ticketing/app
EnvironmentFile=/etc/ticketing.env
ExecStart=/srv/ticketing/app/.venv/bin/gunicorn config.wsgi:application --workers 3 --bind 127.0.0.1:8000 --access-logfile - --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ticketing
sudo systemctl status ticketing
```

## 7. Nginx and HTTPS

Create `/etc/nginx/sites-available/ticketing`:

```nginx
server {
    listen 80;
    server_name tickets.example.com;
    client_max_body_size 20M;

    location /static/ { alias /srv/ticketing/app/staticfiles/; }
    location /media/ { alias /srv/ticketing/app/media/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it and obtain a certificate using your organisation’s approved process (for example Certbot). HTTPS must be in place before enabling production traffic.

## Updating production

For each release: back up PostgreSQL and `media/`, deploy code, install dependencies, run `migrate --noinput`, run `collectstatic --noinput`, then restart `ticketing`. Do not run `makemigrations` on the production server.
