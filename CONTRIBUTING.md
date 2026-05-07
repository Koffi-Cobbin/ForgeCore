# Contributing to ForgeCore

Thank you for your interest in contributing to ForgeCore — a modular backend infrastructure platform built with Django.

ForgeCore is designed as a reusable developer platform providing authentication, storage, email, API keys, and multi-tenant services.

We welcome contributions that improve stability, scalability, developer experience, and architectural clarity.

---

## 🚧 Project Philosophy

Before contributing, understand:

- ForgeCore is a **platform**, not a CRUD application
- Architecture quality is more important than feature quantity
- Services must remain modular and reusable
- Business logic must be separated from API layers
- Provider-based design is mandatory (no hardcoded implementations)

---

## 🧱 Development Principles

All contributions MUST follow:

- Service-layer architecture (no logic in views)
- API versioning (`/api/v1/`)
- Multi-tenancy awareness (organization-first design)
- Provider abstractions for external systems
- No tight coupling to Celery/Redis/Django-Q2 internals
- Clean separation of concerns

---

## 🛠️ Getting Started

### 1. Clone repository
```bash
git clone https://github.com/your-org/forgecore.git
cd forgecore
```

### 2. Create virtual environment
```
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Run migrations
```
python manage.py migrate
```

### 5. Start server
```
python manage.py runserver
```

🧪 Testing

All contributions must include tests where applicable.

## pytest
### 🔀 Pull Request Guidelines
- Keep PRs focused (one feature/fix per PR)
- Write clear commit messages
- Include tests for new functionality
- Ensure no breaking changes without discussion
- Follow existing code style
### ❌ What We Do NOT Accept
- Monolithic or tightly coupled implementations
- Direct external service coupling (no hardcoded providers)
- Business logic inside views or serializers
- Unversioned APIs
- Breaking architectural conventions
### 💬 Discussion First
For major changes, open a discussion or issue before submitting a PR.

Thank you for helping improve ForgeCore 🚀
