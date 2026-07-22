# Application Starter Platform — Developer Edition

A portable, reusable development foundation for modern web applications.

**Version 0.1.0**

---

## A Human–AI Collaboration Project

This project was created through sustained collaboration between:

**ChatGPT + Konstantinos Andritsopoulos**

It was not developed as a simple code-generation exercise.

The platform emerged through continuous dialogue, architectural analysis, implementation, testing, correction, packaging, and verification in real environments.

Konstantinos Andritsopoulos contributed his professional experience in:

- systems analysis,
- application architecture,
- database design,
- operational workflows,
- software usability,
- and the organization of complete information systems.

ChatGPT participated as an architectural, technical, educational, and implementation collaborator.

The central working principle was:

> Artificial intelligence should not merely produce code.  
> It should help people understand, design, test, improve, and create complete systems.

---

## Purpose

Application Starter Platform — Developer Edition provides a tested technical and security foundation for new software projects.

Its purpose is to allow developers to avoid rebuilding the same infrastructure repeatedly and concentrate on:

- the application Domain,
- business rules,
- database entities,
- API endpoints,
- workflows,
- reporting,
- and the final Frontend.

This is a **developer starter platform**, not a finished end-user application.

---

## Included Foundation

### Backend

- FastAPI
- Uvicorn
- SQLAlchemy 2.0
- Alembic migrations
- Pydantic settings
- SQLite support
- External database configuration
- Environment-based configuration

### Authentication and Account Security

- User registration
- Password hashing with Argon2
- Email verification
- Login
- JWT Bearer authentication
- Protected API endpoints
- Forgot-password workflow
- Password-reset workflow
- One-time security tokens
- Token expiration and revocation
- Neutral security responses

### Email

- Gmail configuration
- Custom SMTP configuration
- STARTTLS and secure connection support
- Configurable sender identity
- Email verification messages
- Password-reset messages

### Developer Tools

- Graphical Application Configurator
- OpenAPI contract
- Database migrations
- Automated tests
- Test frontend pages
- Full Python source code
- Application startup command file

---

## Portable Execution

The distribution includes its own private **Python 3.14.6 runtime**.

A system-wide Python installation is not required for:

- installation,
- graphical configuration,
- database migrations,
- initial execution,
- authentication testing,
- or normal demonstration of the platform.

The portable environment contains:

- Python 3.14.6
- Python standard library
- required DLLs
- SSL support
- SQLite support
- `tkinter` for the graphical Configurator
- the project virtual environment
- all installed dependencies

The private Python runtime is connected dynamically to the installed project during setup.

It does not depend on:

- the Windows `PATH`,
- a preinstalled Python version,
- the original development computer,
- or the original Windows username.

---

## Verified Status

The portable Developer Edition was verified after removing the system-wide Python installation.

The following were confirmed:

- private Python runtime loading
- virtual-environment package loading
- SSL
- SQLite
- `tkinter`
- Alembic migrations
- FastAPI startup
- Uvicorn startup
- graphical Configurator
- registration
- email verification
- login
- JWT authentication
- forgot-password workflow
- password-reset workflow
- protected endpoints
- complete end-to-end authentication flow

Automated test result:

```text
139 passed
