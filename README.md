Course Management Tool

REST API for managing courses, users, avatars, and enrollments. Implemented in Python and designed for deployment on Google Cloud Platform using App Engine, Datastore, and Cloud Storage. Auth0 is used for authentication (JWTs). The project exposes a concise set of endpoints to manage users and courses with role-based access controls (admin, instructor, student).

Key features

- Lightweight REST API for course and user management
- Role-based access control enforced via JWTs (Auth0)
- Avatar upload/download/delete using Google Cloud Storage
- Course creation, retrieval, update, and deletion
- Student enrollment management (enroll/unenroll)

Tech stack

- Language: Python 3
- Framework: Flask
- Auth: Auth0 (JWTs)
- Storage: Google Cloud Datastore (entities) and Cloud Storage (avatars)
- Deployment target: Google App Engine

API summary (high level)

The API exposes 13 endpoints covering authentication, user management, avatar operations, course CRUD, and enrollment management. Important endpoints include:

- `POST /users/login` — exchange username/password for an Auth0-issued ID token
- `GET /users` — list users (admin only)
- `GET /users/:id` — retrieve user details (admin or owner)
- `POST /users/:id/avatar` — upload or update a user's avatar (owner only)
- `GET /users/:id/avatar` — retrieve a user's avatar URL (owner only)
- `DELETE /users/:id/avatar` — delete a user's avatar (owner only)
- `POST /courses` — create a course (admin only)
- `GET /courses` — list courses (paginated)
- `GET /courses/:id` — retrieve course details
- `PATCH /courses/:id` — update course fields (admin only)
- `DELETE /courses/:id` — delete a course (admin only)
- `PATCH /courses/:id/students` — modify enrollment (admin or course instructor)
- `GET /courses/:id/students` — list enrolled students (admin or course instructor)

Running locally

Prerequisites

- Python 3.8+ installed
- Google Cloud SDK (for GCP auth and deployment)
- Service account or application default credentials configured for Datastore and Cloud Storage access
- Auth0 tenant and credentials (client ID/secret) configured as environment variables when running in production

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application locally

```bash
python3 main.py
```

Notes and configuration

- The application expects Auth0 configuration and Google Cloud credentials to be available in the runtime environment. See `main.py` for constants (Auth0 client ID, client secret, and domain) and the `AVATAR_BUCKET` name. Replace hard-coded values with secure environment variables before deploying.
- Pagination on `GET /courses` uses `limit` and `offset` query parameters. Default page size in the implementation is 3.
- Role checks and error handling logic live in `error_handling.py` and are used consistently across endpoints.

Project layout

- `main.py` — Flask app with all endpoints and business logic
- `error_handling.py` — JWT validation and authorization helpers
- `requirements.txt` — Python dependencies
- `app.yaml` — App Engine deployment descriptor
