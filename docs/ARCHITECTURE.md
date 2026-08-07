# Architecture

## Architecture Principle

Start with a modular monorepo. Do not create microservices without a concrete need.

The backend is a modular Django monolith. Vision is a separate service because it has different CV/ML dependencies and resource requirements.

## Monorepo Layout

```text
foodai-ecosystem/
├── backend/
├── frontend/
├── services/
│   └── vision/
├── infra/
├── docs/
├── scripts/
├── .github/
├── AGENTS.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## Components

### Backend

Target stack:

- Python.
- Django.
- Django REST Framework.
- PostgreSQL.
- Redis.
- Celery.

Responsibilities:

- authentication and authorization;
- user profile and privacy controls;
- meal diary;
- nutrition catalog and nutrient calculations;
- photo metadata and private object storage references;
- orchestration of Vision jobs;
- AI assistant boundaries and safety logic;
- export and deletion flows;
- admin audit logging.

### Vision Service

Target stack:

- Python.
- FastAPI.
- OpenCV.
- ML/CV libraries only when justified by a specific task.

Responsibilities:

- validate uploaded image format;
- strip EXIF/geolocation before analysis or storage when applicable;
- run food/product/ingredient recognition;
- estimate portion and mass;
- return structured recognition candidates to the backend.

Vision does not own user accounts, diaries, billing, or long-term product data.

### Frontend

Target stack:

- Next.js.
- TypeScript.
- Responsive PWA.

Responsibilities:

- photo capture/upload UX;
- result confirmation and correction;
- diary views;
- goals and progress views;
- user-facing AI workflows with safety boundaries.

### Infrastructure

Initial local dependencies:

- PostgreSQL.
- Redis.
- MinIO as private S3-compatible object storage.

Production target:

- managed PostgreSQL;
- managed Redis or compatible queue broker;
- private S3-compatible object storage;
- deny-by-default networking and least-privilege service credentials.

## Core Data Flow

1. Frontend uploads a food photo to the backend.
2. Backend validates user permissions, upload size, MIME, and actual file format.
3. Backend removes sensitive metadata where needed and stores the photo in private object storage.
4. Backend sends the minimal necessary image reference or payload to Vision.
5. Vision returns structured recognition candidates.
6. Backend calculates nutrition using the product catalog and stores a pending result.
7. User confirms or corrects the result.
8. Backend stores confirmed diary data and uses it for analysis.

## API Stability

No stable public API exists yet. Future API changes must be documented in `docs/API.md`, and breaking changes require an explicit decision in `docs/DECISIONS.md`.

