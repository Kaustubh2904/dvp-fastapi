# Digital Verification Portal (DVP) Backend API

This repository contains the backend code for the Digital Verification Portal (DVP) built using **FastAPI**. It provides comprehensive APIs to manage companies, employees, background verification documents, subscriptions, role-based access control (RBAC), real-time notifications, chat, and background tasks.

---

## 🏗️ Architecture & Technology Stack

The project follows a robust, multi-layered, asynchronous architecture using the following core technologies:

*   **FastAPI:** High-performance, asynchronous Python web framework.
*   **PostgreSQL:** Primary relational database holding core domain entities (Users, Companies, Subscriptions, Documents, etc.).
*   **MongoDB:** NoSQL database used for flexible schema storage like Chat Messages and Audit Logs (detailed entity history).
*   **Redis:** In-memory store utilized as the message broker for background task queues and ephemeral caching (OTP/Rate Limiting).
*   **ARQ:** High-performance asynchronous job queues leveraging Redis for background tasks (e.g., sending emails, running daily subscription chron jobs).
*   **SQLAlchemy 2.0 (Async):** Next-generation asynchronous ORM connecting to PostgreSQL via the `psycopg3` driver.
*   **Alembic:** Database migration tool mapping Python SQLAlchemy models to PostgreSQL DDL schemas.
*   **Docker & Docker Compose:** Containerization stack.

---

## 🐳 Docker Services & Infrastructure

The application runs using a multi-container Docker Compose setup defined in `docker-compose.yml`.

### Services

1.  **`postgres`** (`postgres:16-alpine`)
    *   **Role:** The primary relational database.
    *   **Storage:** Persists data to the `postgres_data` volume.
2.  **`mongodb`** (`mongo:7`)
    *   **Role:** The secondary NoSQL database for unstructured data and audit logs.
    *   **Storage:** Persists data to the `mongodb_data` volume.
3.  **`redis`** (`redis:7-alpine`)
    *   **Role:** Key-value store acting as the message queue broker for ARQ and for fast in-memory caching.
    *   **Storage:** Persists data to the `redis_data` volume.
4.  **`migrate`** (Custom Image: `dvp-fastapi-migrate`)
    *   **Role:** An ephemeral, single-run container. It waits for PostgreSQL to be healthy, executes `alembic upgrade head` to ensure the database schema is up-to-date, and then exits cleanly.
    *   **Dependency Chain:** The application and worker services will only start once this container reports `service_completed_successfully`.
5.  **`app`** (Custom Image: `dvp-fastapi-app`)
    *   **Role:** The primary API web server running FastAPI via Uvicorn.
    *   **Ports:** Exposed on port `8000`.
    *   **Storage:** Mounts the `uploads_data` volume to persist uploaded verification documents.
6.  **`worker`** (Custom Image: `dvp-fastapi-worker`)
    *   **Role:** The ARQ background task processor. It does not handle HTTP requests; instead, it listens to Redis for jobs enqueued by the `app` (e.g., OTP emails, password resets) and runs scheduled cron tasks (e.g., midnight subscription expiry checks).

### Running the Stack
```bash
# Build the containers and bring up the full infrastructure
docker compose up --build -d

# View live logs of the running API and worker
docker compose logs -f app worker

# Teardown the stack (removes containers, networks)
docker compose down

# Teardown and wipe databases (WARNING: deletes all volumes)
docker compose down -v
```

---

## 📂 Project Structure & Code Files

The source code sits inside the `app/` directory and follows a strict layered architecture pattern.

### `app/core/` (Core Configuration)
*   `config/settings.py`: Uses `pydantic-settings` to load and validate all environment variables (`.env`).
*   `database/postgres.py`: Defines the async SQLAlchemy engine, session maker, and dependency injection `get_db()`.
*   `database/mongodb.py`: Defines the `AsyncIOMotorClient` for connecting to MongoDB.
*   `database/redis.py`: Manages the Redis connection pool.
*   `security/`: Contains JWT token generation, password hashing (argon2), and RBAC dependency injection logic (e.g., `require_admin`, `require_superadmin`).

### `app/models/` (Database Models)
Defines the structure of PostgreSQL tables using SQLAlchemy 2.0 Declarative mapping.
*   `base.py`: The `DeclarativeBase` all models inherit from.
*   `user.py`, `role.py`: Identity management and role assignments.
*   `company.py`, `department.py`, `employee.py`: Organizational hierarchy.
*   `subscription.py`: Billing status and tier limits for companies.
*   `document.py`: Employee background verification documents.
*   `otp.py`, `password_reset.py`: Ephemeral authentication flow tables.
*   `notification.py`, `audit_log.py`: System tracking and alerts.

### `app/schemas/` (Pydantic Models)
Defines the input validation and output serialization structures (DTOs). Ensures strict typing of HTTP payloads. Separated out by domain (e.g., `auth.py`, `company.py`, `employee.py`).

### `app/repositories/` (Data Access Layer)
Abstracts complex SQL queries away from business logic.
*   Each domain entity (e.g., `company_repository.py`) has a repository class containing methods to execute raw SQLAlchemy ORM commands against the Postgres database.

### `app/services/` (Business Logic Layer)
Orchestrates the application logic, combining multiple repositories and external services.
*   e.g., `subscription_service.py` handles the logic of checking employee limits, upgrading tiers, or suspending expired companies. `auth_service.py` handles the complex orchestration of generating an OTP, saving it to Postgres, and enqueueing a Redis background task to email the user.

### `app/routes/` (Controllers / API Endpoints)
FastAPI router definitions grouping the HTTP endpoints by domain. This layer receives the HTTP requests, delegates to the `services` layer, and returns the response.

### `app/tasks/` (Background Jobs)
*   `worker.py`: Entry point for the ARQ worker. Defines the background functions (`send_otp_email_job`, `run_subscription_checks`) and standard daily cron jobs.
*   `queue.py`: Helper functions utilized by the `app` to enqueue jobs into Redis.

### Root Level
*   `alembic/`: Contains the database migration scripts (`versions/`).
*   `alembic.ini` & `env.py`: Alembic runtime configuration.
*   `Dockerfile`: Multi-stage Docker build file using `uv` (Astral's fast Python package manager) for creating optimized, lightweight production images.
*   `docker-compose.yml`: Local infrastructure orchestrator.
*   `pyproject.toml` & `uv.lock`: Python package dependency specifications.

---

## 📡 Complete List of API Endpoints

All APIs are prefixed with `/api/v1` (as configured in `settings.py`). FastAPI automatically generates Swagger documentation available at `http://localhost:8000/docs` while the server is running.

### 🔐 Authentication (`/api/v1/auth`)
*   `POST /login`: Authenticate and receive access + refresh tokens. *(Blocks access returning a 403 if forced password-reset is required)*
*   `POST /refresh`: Obtain a new access token using a refresh token.
*   `POST /otp/generate`: Trigger an OTP to be sent to a registered email.
*   `POST /otp/login`: Authenticate using an email and an OTP. *(Blocks access returning a 403 if forced password-reset is required)*
*   `POST /forgot-password`: Generate a password reset link.
*   `POST /reset-password`: Set a new password using a valid reset token. *(Clears the forced password-reset state)*
*   `POST /change-password`: Change password for an authenticated user.
*   `GET /me`: Retrieve the currently authenticated user's profile.


### 🏢 Companies (`/api/v1/companies`)
*   `POST /`: Register a new company. *(Requires Superadmin)*
*   `GET /`: List all registered companies. *(Requires Superadmin)*
*   `GET /{company_id}`: Get specific company details.
*   `PUT /{company_id}`: Update company information.
*   `GET /{company_id}/statistics`: Get dashboard metrics for the company. *(Requires Admin)*
*   `GET /{company_id}/employees`: List all employees of the company. *(Requires Admin)*

### 📁 Departments (`/api/v1/departments`)
*   `POST /`: Create a new department inside a company. *(Requires Admin)*
*   `GET /company/{company_id}`: List all departments for a given company.
*   `GET /{department_id}`: Get specific department details.
*   `PUT /{department_id}`: Update department information. *(Requires Admin)*
*   `DELETE /{department_id}`: Remove a department. *(Requires Admin)*
*   `POST /{department_id}/employees/{employee_id}`: Assign an employee to the department. *(Requires Admin)*
*   `DELETE /{department_id}/employees/{employee_id}`: Remove an employee from the department. *(Requires Admin)*

### 👥 Employees (`/api/v1/employees`)
*   `POST /`: Create a new employee invite. *(Requires Admin)*
*   `POST /bulk-upload`: Upload a CSV to bulk invite employees. *(Requires Admin)*
*   `POST /register`: Complete employee registration (accept invite).
*   `GET /{employee_id}`: Get details of an employee. *(Notes field visible to Admin/HR roles only)*
*   `PUT /{employee_id}`: Update an employee's details. *(Notes field modifiable by Admin/HR roles only)*
*   `POST /{employee_id}/upload-letters`: Upload unique Offer and Joining Letters for the candidate. *(Requires Admin)*
*   `POST /{employee_id}/send-letters`: Dispatch the uploaded Offer and Joining Letters to the candidate via email. *(Requires Admin, requires all employee docs to be verified)*


### 📄 Documents & Verification (`/api/v1/documents`)
*   `POST /upload`: Upload a verification document (AADHAAR, PAN, etc.) for an employee.
*   `POST /{document_id}/verify`: Mark an uploaded document as manually verified. *(Requires Admin)*
*   `POST /{document_id}/reject`: Reject an uploaded document with remarks. *(Requires Admin)*
*   `POST /digilocker-fetch`: Trigger an automated fetch of documents via the DigiLocker integration.
*   `GET /employee/{employee_id}`: Get all verification documents for a specific employee.

### 🔔 Notifications (`/api/v1/notifications`)
*   `GET /`: Get all notifications for the authenticated user.
*   `PUT /read-all`: Mark all notifications as read.
*   `PUT /{notification_id}/read`: Mark a single notification as read.

### 💳 Subscriptions (`/api/v1/subscriptions`)
*   `POST /`: Create or upgrade a company subscription tier. *(Requires Superadmin)*
*   `PUT /{subscription_id}`: Modify an existing subscription. *(Requires Superadmin)*
*   `GET /dashboard`: Get global platform subscription metrics. *(Requires Superadmin)*
*   `GET /expiring`: List companies with subscriptions expiring soon. *(Requires Superadmin)*
*   `POST /trigger-checks`: Manually trigger the background expiry check cron job. *(Requires Superadmin)*

### 🛡️ Superadmin Management (`/api/v1/superadmin`)
*   `GET /users`: List all platform users across all companies. *(Requires Superadmin)*
*   `POST /users`: Manually create a user with a specific role. *(Requires Superadmin)*
*   `PUT /users/{user_id}`: Modify a user's role or status. *(Requires Superadmin)*
*   `DELETE /users/{user_id}`: Hard delete a user from the system. *(Requires Superadmin)*

### 💬 Chat & Websockets
*   `GET /api/v1/chat/conversations`: Get all chat conversations for the user.
*   `GET /api/v1/chat/conversations/{conversation_id}/messages`: Retrieve chat history for a specific conversation.
*   `PUT /api/v1/chat/conversations/{conversation_id}/read`: Mark a conversation as read.
*   `WEBSOCKET /api/v1/ws/chat`: Real-time bidirectional connection for streaming chat messages.
