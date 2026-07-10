# Implementation Notes

This repository is a FastAPI backend for the Digital Verification Portal (DVP). The codebase is already organized into a layered architecture, and the current implementation wires together authentication, company and employee management, documents, subscriptions, notifications, chat, and background processing.

## What Is Already Implemented

### Application bootstrap
The main application is created in [app/main.py](app/main.py). It:

- loads configuration from `app/core/config/settings.py`
- initializes logging
- starts Redis on application startup when available
- checks MongoDB availability during startup
- creates the uploads directory if it does not exist
- mounts uploaded files under `/static/uploads`
- registers a global exception handler
- includes the API routers under the `/api/v1` prefix
- exposes `/health` and `/` endpoints for service monitoring

### Configuration
Runtime settings are defined in [app/core/config/settings.py](app/core/config/settings.py). The app reads its configuration from `.env` when present and falls back to defaults for local development.

Important settings already wired in include:

- API version prefix: `/api/v1`
- PostgreSQL connection details
- MongoDB connection details
- Redis connection details
- JWT and token expiry values
- OTP and password reset expiry values
- upload directory path

### Persistence layers
The project uses three storage backends:

- PostgreSQL for the main transactional data
- MongoDB for flexible data such as chat and audit-style records
- Redis for caching and background task coordination, with an in-memory fallback when Redis is unavailable

The database modules are already implemented in:

- [app/core/database/postgres.py](app/core/database/postgres.py)
- [app/core/database/mongodb.py](app/core/database/mongodb.py)
- [app/core/database/redis.py](app/core/database/redis.py)

### Request handling flow
The API follows a clear route -> service -> repository pattern.

- routers under [app/routes/](app/routes) define HTTP endpoints by domain
- services under [app/services/](app/services) contain the business rules
- repositories under [app/repositories/](app/repositories) handle SQLAlchemy queries and persistence
- schemas under [app/schemas/](app/schemas) define request and response models
- models under [app/models/](app/models) define the PostgreSQL entities

### Authentication and account flows
The auth service in [app/services/auth_service.py](app/services/auth_service.py) already implements the main identity flows:

- email/password authentication
- access and refresh token generation
- token refresh validation
- SaaS company registration that creates both the company and the admin user
- OTP generation and verification
- forgot-password and reset-password flows (where password-reset tokens are one-time use and do not expire on time limits, ensuring employees can access their onboarding reset links regardless of when they open them)
- forced employee password reset upon manual/bulk onboarding: newly created employee accounts are initialized with `must_change_password=True` and a generated reset token is sent to their email. The `/auth/login` endpoint restricts active session generation until a password reset consumes the token.
- audit logging after sensitive actions

Portal access is now role-aware. The user model includes `SUPERADMIN`, `MARKETING`, and `TECHNICAL_TEAM` in addition to the operational `ADMIN` and `EMPLOYEE` roles. The portal login path accepts the portal-facing roles, while the normal login path remains for regular application users.

OTP and reset-token data is persisted in PostgreSQL, and OTP values are also cached in Redis when possible.

### Background tasks
Background processing is already wired through ARQ and FastAPI background tasks.

- [app/tasks/queue.py](app/tasks/queue.py) sends jobs to Redis-backed ARQ when Redis is healthy
- if Redis is not available, it falls back to in-process FastAPI background tasks
- [app/tasks/worker.py](app/tasks/worker.py) defines the worker job functions
- the worker already includes a daily cron job for subscription expiry checks

The implemented jobs include:

- sending OTP emails
- sending onboarding emails
- sending password-reset emails
- running subscription expiry and suspension checks

Superadmin bootstrap credentials are no longer hardcoded in the seed script. They are read from environment variables through the settings layer before the first superadmin account is created.

### Tickets
A lightweight ticket workflow is now available through MongoDB-backed routes. Admin and HR users can raise tickets from the company side, and the technical team or superadmin can list, view, and reply to them. Ticket replies are stored with responder metadata and the ticket status advances when a support reply is added.

### Subscription Management
The subscription module is now plan-driven and company-scoped. Plans live in PostgreSQL via a dedicated plan catalog, and companies no longer mutate subscriptions directly. Instead, tenant admins and HR users create subscription requests for upgrades, downgrades, and renewals, while SuperAdmin reviews and approves or rejects them.

The module now includes:

- database-backed plans for Free, Basic, Pro, Premium, and Custom
- one-time Free trial handling with trial consumption tracking
- subscription requests with approval and rejection flow
- prorated upgrade values for review-only display
- scheduled downgrades at the next billing cycle
- monthly usage tracking for employee snapshots, document uploads, and storage consumption
- centralized feature and quota checks reused by tenant write operations
- read-only expired-subscription behavior for login, dashboard, document viewing, notifications, renewal requests, and support tickets

Current seeded subscription tiers and their feature profile:

| Tier | Admins | Employees | Monthly document uploads | Storage | Chat | API | Analytics | Ticket priority | White-label | Trial | Price |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: |
| Free | 1 | 10 | 100 | 1 GB | No | No | No | Low | No | 14 days | 0 |
| Basic | 1 | 50 | 500 | 5 GB | Yes | No | No | Low | No | 14 days | 99.00 |
| Pro | 2 | 200 | 2,500 | 20 GB | Yes | Yes | Yes | Medium | Yes | 14 days | 299.00 |
| Premium | 5 | 1,000 | 10,000 | 100 GB | Yes | Yes | Yes | High | Yes | 14 days | 999.00 |
| Custom | 10 | 5,000 | 50,000 | 200 GB | Yes | Yes | Yes | High | Yes | No trial | SuperAdmin assigned |

These values are database-driven through [app/models/subscription_plan.py](app/models/subscription_plan.py) and seeded in [alembic/versions/0003_subscription_module_upgrade.py](alembic/versions/0003_subscription_module_upgrade.py). SuperAdmin can create additional custom plan records without changing the code path.

### Background Jobs And Email
ARQ now runs daily expiry checks, scheduled subscription transitions, and monthly usage resets. Subscription lifecycle events generate audit logs and in-app notifications, and subscription-related email delivery is queued through a reusable email service with an email log table so delivery failures do not roll back subscription updates.

### Real-time chat
WebSocket chat support is already present.

- [app/services/websocket_service.py](app/services/websocket_service.py) manages active connections and presence updates
- it validates whether two users are allowed to communicate based on role and company
- connection and disconnection events are logged through the chat service

### Cross-cutting middleware
The app already applies common middleware in [app/core/middleware.py](app/core/middleware.py):

- request timing and access logging
- basic security headers

## Feature Areas That Are Already Wired In

The current router set shows the implemented product areas:

- authentication and account recovery
- superadmin user management
- companies and organizational structure
- employees and invitations
- documents and verification
- subscriptions and expiry checks
- notifications
- chat and websocket transport
- ticket handling for support workflows

Role-based access in the portal is split as follows:

- superadmin can access every portal area, including ticket resolution
- marketing can access subscription-related routes only
- technical team can access ticket-related routes and replies
- admin-side users can create support tickets from the company side

## How It Works End To End

1. A request enters FastAPI through `app/main.py`.
2. Middleware records timing and adds security headers.
3. The matching router delegates the request to a service.
4. The service uses repositories to read or write PostgreSQL data.
5. When needed, the service also touches Redis, MongoDB, or background tasks.
6. Responses are returned as Pydantic schema objects or structured JSON.
7. Background jobs run through ARQ or FastAPI background execution depending on Redis availability.

## Operational Checks Already Present

The app includes runtime checks for:

- PostgreSQL connectivity
- Redis connectivity
- MongoDB connectivity

The `/health` endpoint returns component-level status so the stack can be monitored by orchestration tooling.

## Notes

This file documents the current implementation state based on the existing code structure and entrypoints. It is meant as a living summary of what is already in place and how the pieces connect.
