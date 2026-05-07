# ForgeCore

A modular API-first backend infrastructure platform built with Django and Django REST Framework.

## Overview

ForgeCore is a reusable backend infrastructure platform providing:
- JWT Authentication & User Management
- Organizations / Multi-tenancy
- API Key Management (hashed storage, never reversible)
- File Storage (provider-abstracted: local, S3-ready)
- Email Service (provider-abstracted with logs)
- Audit Logging
- Health Check

## Project Structure

```
backend_platform/
├── apps/
│   ├── common/         # BaseModel, exceptions, responses, pagination, TaskDispatcher
│   ├── users/          # Custom user model, profile management
│   ├── organizations/  # Organizations, memberships, roles
│   ├── authentication/ # JWT login, register, logout, password reset, email verify
│   ├── api_keys/       # Secure API key generation, hashing, authentication
│   ├── email_service/  # Email providers, logs, async dispatch
│   ├── storage_service/ # File upload, provider abstraction (local/S3)
│   ├── audit_logs/     # Action tracking, request tracing
│   └── health/         # Health check endpoint
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── tests/
├── manage.py
└── start.sh
```

## API Endpoints

All APIs are versioned under `/api/v1/`:

- `GET /api/v1/health/` — Health check
- `POST /api/v1/auth/register/` — Register
- `POST /api/v1/auth/login/` — Login (returns JWT)
- `POST /api/v1/auth/logout/` — Logout (blacklists refresh token)
- `POST /api/v1/auth/token/refresh/` — Refresh access token
- `POST /api/v1/auth/verify-email/` — Verify email
- `POST /api/v1/auth/password-reset/` — Request password reset
- `POST /api/v1/auth/password-reset/confirm/` — Confirm password reset
- `GET/PATCH /api/v1/users/me/` — Get/Update current user
- `POST /api/v1/users/me/change-password/` — Change password
- `GET/POST /api/v1/organizations/` — List/Create organizations
- `GET/PATCH /api/v1/organizations/<id>/` — Organization detail
- `GET/POST /api/v1/organizations/<id>/members/` — Members
- `DELETE /api/v1/organizations/<id>/members/<id>/` — Remove member
- `GET/POST /api/v1/organizations/<id>/api-keys/` — API keys
- `DELETE /api/v1/organizations/<id>/api-keys/<id>/` — Revoke key
- `GET/POST /api/v1/organizations/<id>/files/` — File storage
- `GET/DELETE /api/v1/organizations/<id>/files/<id>/` — File detail
- `POST /api/v1/organizations/<id>/emails/send/` — Send email
- `GET /api/v1/organizations/<id>/emails/logs/` — Email logs
- `GET /api/v1/organizations/<id>/audit-logs/` — Audit logs

## Documentation

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI Schema: `/api/schema/`

## Tech Stack

- Django 5 + Django REST Framework
- PostgreSQL (via Replit managed DB)
- JWT via djangorestframework-simplejwt
- Task dispatch via TaskDispatcher abstraction (sync/django-q2)
- OpenAPI via drf-spectacular
- Gunicorn for production

## Running Locally

The app starts automatically via the "Start application" workflow which:
1. Runs Django migrations
2. Collects static files
3. Starts Gunicorn on port 5000

## Environment Variables

See `backend_platform/.env.example` for all configurable options.
Key variables:
- `SECRET_KEY` — Django secret key
- `DATABASE_URL` / `PG*` — PostgreSQL credentials (set automatically by Replit)
- `TASK_MODE` — `sync` (default) or `django_q`
- `STORAGE_PROVIDER` — `local` (default) or `s3`
- `EMAIL_BACKEND` — Django email backend

## User Preferences

- Modular monolith architecture
- Service layer pattern (business logic in services, not views)
- Provider abstractions for email and storage
- TaskDispatcher abstraction for async tasks
- All APIs versioned under /api/v1/
- UUID primary keys throughout
- Organization-aware resources
