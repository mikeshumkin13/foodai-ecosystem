# Security

FoodAI Ecosystem follows privacy-by-design and security-by-design from the start.

## Principles

- Least privilege.
- Deny by default.
- Data minimization.
- UUIDs instead of sequential public IDs where justified.
- Secrets only through environment variables.
- No committed `.env` files.
- Secure Django password hashing.
- CSRF protection.
- Strict CORS allowlist.
- Rate limiting.
- Object-level permissions.
- Private photos and private object storage.
- Sensitive data redaction in logs.

## Sensitive Data

Treat the following as sensitive:

- user photos;
- food diary contents;
- health profile data;
- AI conversations;
- access tokens;
- passwords;
- support access logs;
- export files.

Logs must not contain passwords, tokens, health profile data, user photos, or other sensitive content. Tokens and secrets must be redacted.

## Upload Security

Food photo uploads must include:

- authentication and object-level authorization;
- file size limits;
- MIME validation;
- actual file format validation;
- EXIF/geolocation stripping;
- malware scanning when appropriate for the deployment tier;
- private storage by default.

## Roles And Access

- `anonymous`: no private data access.
- `user`: access only to own data.
- `support`: no default access to diary contents, food photos, AI dialogs, or health profile.
- `content_manager`: access to catalog and content only.
- `admin`: permissions-based administration.
- `superuser`: technical access only, not daily work.

Support access to sensitive data requires a separate procedure and audit logging.

## AI Safety

AI receives only minimal necessary user context.

AI must not:

- diagnose;
- prescribe medication;
- replace a doctor, licensed nutritionist, or psychologist;
- make medical decisions independently.

Potentially dangerous situations require safety classification and safe response logic before production.

## User Rights

The system must support:

- account deletion;
- deletion of related user data;
- user data export;
- clear handling of private photos and derived data.

Before production, legal requirements must be reviewed for every launch country.

