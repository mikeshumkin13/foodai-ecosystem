# Decisions

## ADR-0001: Use A Monorepo

Date: 2026-08-07

Status: Accepted

Decision:

FoodAI Ecosystem starts as a monorepo with `backend`, `frontend`, `services/vision`, `infra`, `docs`, and `scripts`.

Rationale:

- shared product and security documentation stays close to code;
- local development can be coordinated with Docker Compose;
- early-stage architecture remains easy to change without cross-repository overhead.

Consequences:

- CI must be aware of multiple project areas;
- ownership boundaries must be documented clearly;
- unrelated changes should still be kept in separate commits and PRs.

## ADR-0002: Use A Modular Django Monolith For Backend

Date: 2026-08-07

Status: Accepted

Decision:

The backend starts as a modular Django monolith. Do not split business capabilities into microservices without a concrete operational or domain need.

Rationale:

- product workflows are tightly connected at MVP stage;
- data consistency matters for diary, photos, nutrition calculations, permissions, exports, and deletion;
- a monolith reduces deployment and observability complexity.

Consequences:

- internal Django apps should have clear boundaries;
- shared models and permissions must be designed carefully;
- future extraction remains possible only after real pressure appears.

## ADR-0003: Keep Vision As A Separate Service

Date: 2026-08-07

Status: Accepted

Decision:

Vision is a separate FastAPI service under `services/vision`.

Rationale:

- CV/ML dependencies differ from backend dependencies;
- Vision may need different CPU/GPU resources;
- image processing failures should be isolated from core diary and auth flows.

Consequences:

- backend owns user data and long-term persistence;
- Vision receives only minimal necessary image context;
- the backend/Vision contract must be tested.

## ADR-0004: Store User Photos In Private S3-Compatible Object Storage

Date: 2026-08-07

Status: Accepted

Decision:

Food photos are private by default and stored in S3-compatible object storage. Local development may use MinIO.

Rationale:

- photos are sensitive user data;
- object storage is a better fit than application filesystem storage;
- S3 compatibility keeps provider choice open.

Consequences:

- no public buckets;
- signed URLs only when needed;
- object-level authorization is required;
- lifecycle, deletion, and export behavior must be implemented deliberately.

