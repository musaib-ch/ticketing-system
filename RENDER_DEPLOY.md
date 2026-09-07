# Render + Supabase deployment

## Web service

This repository is prepared for a Render Python web service. The included `render.yaml` runs migrations and `collectstatic` during build and starts Gunicorn. You can also enter these commands manually in Render:

**Build command**
```
pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput
```

**Start command**
```
gunicorn config.wsgi:application --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -
```

## Supabase PostgreSQL

Use the **Session Pooler** connection details from Supabase Connect because IPv4-only hosts such as Render should use the pooler. Set:

```ini
POSTGRES_DB=postgres
POSTGRES_USER=postgres.<project-ref>
POSTGRES_PASSWORD=<supabase-db-password>
POSTGRES_HOST=<supabase-session-pooler-host>
POSTGRES_PORT=5432
POSTGRES_SSLMODE=require
```

Do not commit these values.

## Required production variables

```ini
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=<your-render-host>.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-render-host>.onrender.com
SITE_URL=https://<your-render-host>.onrender.com
MS_TENANT_ID=<tenant-id>
MS_CLIENT_ID=<app-client-id>
MS_CLIENT_SECRET=<client-secret>
```

Microsoft Entra redirect URI:
`https://<your-render-host>.onrender.com/manage/auth/microsoft/callback/`

## Persistent uploads (required in production)

Django does not serve local media files at all when `DJANGO_DEBUG=False`
(the `/media/` URL isn't even registered), so ticket attachments,
knowledge-base files, and branding images will 404 immediately - not just
after a redeploy - unless S3-compatible storage is configured. `settings.py`
enforces this: the app refuses to start in production without
`AWS_STORAGE_BUCKET_NAME` set. Configure a Supabase Storage bucket:

```ini
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_ENDPOINT_URL=https://<project-ref>.storage.supabase.co/storage/v1/s3
AWS_ACCESS_KEY_ID=<supabase-s3-access-key>
AWS_SECRET_ACCESS_KEY=<supabase-s3-secret-key>
AWS_S3_REGION_NAME=ap-southeast-1
AWS_S3_ADDRESSING_STYLE=path
AWS_QUERYSTRING_AUTH=True
```

Keep the bucket private when ticket attachments contain HR information.

## Background jobs

The portal contains Celery tasks for inbound email and SLA/auto-close rules. A web service does **not** execute Celery workers/beat automatically. Configure a separate worker/scheduler only if you need these features. The normal ticket portal works without Celery; inbound email and timed rules simply will not run until a worker/beat is provided.

## First deployment checklist

1. Set all required environment variables.
2. Deploy.
3. Confirm Render build completes `migrate` and `collectstatic`.
4. Open `/accounts/login/`.
5. Test Microsoft SSO.
6. Create a test ticket.
7. Test assignment, reply, close and reopen flows.
8. Upload a test attachment and verify it remains after a redeploy if Supabase Storage is configured.
9. Run `python manage.py check --deploy` locally against production-like environment variables before go-live.
