# Roadmap

## Phase 0: Foundation

- Create repository memory and engineering rules.
- Establish monorepo structure.
- Document architecture, security, API principles, and decisions.
- Add basic local infrastructure placeholders.

## Phase 1: MVP Backend

- Scaffold Django project.
- Add PostgreSQL, Redis, Celery integration.
- Implement authentication and user model strategy.
- Implement roles and object-level permissions.
- Add food photo upload with size, MIME, real format validation, EXIF stripping, and private storage.
- Add meal diary primitives.
- Add nutrition catalog primitives.
- Add API tests and migrations.

## Phase 2: Vision MVP

- Scaffold FastAPI Vision service.
- Add image validation tests.
- Add recognition contract between backend and Vision.
- Start with deterministic or stub recognition where model quality is not yet available.
- Add CV/ML dependencies only when required.

## Phase 3: Frontend MVP

- Scaffold Next.js PWA.
- Add auth flow.
- Add photo upload and recognition review UX.
- Add diary and daily summary views.
- Add frontend tests.

## Phase 4: AI Assistants and Safety

- Add AI nutrition assistant with minimal necessary context.
- Add safety classification and escalation flows.
- Add AI history access controls.
- Add redaction rules for logs and prompts.

## Phase 5: Growth Features

- Workouts.
- Goals.
- Progress charts.
- Personalization.
- Subscription.
- Mobile app.
- HealthKit and Health Connect.
- Smart scales and wearables.
- B2B API.

## Before Production

- Legal review for launch countries.
- Security review.
- Privacy review.
- Threat model update.
- Backup and disaster recovery checks.
- Operational monitoring and incident response process.

