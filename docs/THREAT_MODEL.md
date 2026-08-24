# Threat Model / Модель угроз

Last updated / Обновлено: 2026-08-24

FoodAI Ecosystem находится на MVP/Beta foundation-стадии. Этот документ описывает текущую модель
угроз и baseline mitigations; он не означает, что система полностью безопасна.

## Assets / Активы

- Учетные записи пользователей: email, password hash, session cookies, auth/reset/email tokens.
- Приватные пользовательские данные: nutrition profile, sensitive nutrition restrictions, meals,
  diary aggregates, food scans, workout plans/logs, AI/wellbeing history.
- Фотографии еды и derived scan results: private object key, checksum, labels, confidence, portion
  estimates, nutrient snapshots.
- Privacy controls: export, deletion workflows, consent settings, model improvement consent.
- Administrative data: role groups, Django Admin access, read-only admin audit log.
- Service credentials and infrastructure secrets: `DJANGO_SECRET_KEY`, database credentials, Redis
  password, future object storage credentials, AI provider secrets.
- Internal service contracts: backend-to-Vision requests, Celery task payloads, Redis broker/cache.
- Source code, CI configuration and dependency manifests.

## Actors / Участники

- `anonymous`: неавторизованный пользователь или внешний сканер.
- `user`: обычный пользователь, которому доступны только собственные данные.
- `support`: ограниченная операционная роль без приватных данных по умолчанию.
- `content_manager`: управляет каталогами и справочниками, но не приватными дневниками.
- `admin`: административная роль с выданными permissions.
- `superuser`: технический emergency/system доступ Django.
- Internal services: backend, PostgreSQL, Redis, Celery worker, Vision service, private object
  storage.
- External dependencies/providers: GitHub Actions, package registries, Docker Hub, Hugging Face,
  future AI/storage/email providers.
- Adversaries: internet attacker, compromised browser/session, malicious or curious insider,
  compromised dependency, compromised internal service, misconfigured production deployment.

## Trust Boundaries / Границы доверия

- Browser frontend ↔ backend API: cookie/session authentication, CSRF, CORS allowlist.
- Backend API ↔ PostgreSQL: application-owned data boundary; SQL access through Django ORM.
- Backend/Celery ↔ Redis: broker/cache boundary; task payloads must remain minimal.
- Backend/Celery ↔ Vision service: internal HTTP boundary; Vision receives only prepared object
  reference and not full user profile/diary/history.
- Backend ↔ private object storage: photo bytes/object keys stay private; API does not expose
  permanent public URLs.
- Backend ↔ email delivery: raw verification/reset tokens are sent only out-of-band and stored only
  as hashes.
- Repository/CI ↔ dependency registries: third-party packages, Docker images and model weights are
  supply-chain inputs.
- Staff/Admin UI ↔ production data: Django Admin and support/content permissions are least-privilege
  boundaries.

## Threats And Mitigations / Угрозы и меры

| Area | Threat | Current mitigations |
| --- | --- | --- |
| Authentication | Brute-force login, token theft, weak password handling. | Django password hashing, session cookies instead of browser bearer token storage, scoped auth throttles, password validators, raw reset/verification tokens stored only as hashes. |
| Authorization / IDOR | User accesses another user's UUID resource. | Owner-only querysets, centralized permissions, deny-by-default DRF permissions, API tests for UserProfile, nutrition profile/restrictions, meals, food scans, workout plans/logs, Privacy Center deletion. |
| CSRF | Cross-site unsafe requests abusing session cookies. | `CsrfViewMiddleware`, explicit CSRF enforcement on public auth POST endpoints, frontend CSRF bootstrap, tests for CSRF rejection. |
| CORS | Credentialed requests from untrusted origins. | Explicit `CORS_ALLOWED_ORIGINS`; new production system checks reject wildcard/HTTP origins. |
| XSS | Token/session exfiltration or unsafe HTML rendering. | No browser access token storage, frontend linter blocks `localStorage`/`sessionStorage`, React default escaping, no `dangerouslySetInnerHTML` found in current frontend. CSP remains a future hardening item. |
| SQL injection | User-controlled SQL fragments. | Django ORM is used for application queries; only `wait_for_dependencies` uses static `SELECT 1`; no `raw`, `RawSQL` or interpolated SQL in app code found in review. |
| SSRF | Backend calls attacker-controlled URL. | Vision calls go through `integrations.vision.client` and `VISION_SERVICE_URL` environment config, not user input; no generic URL fetch endpoint. Production checks now reject HTTP frontend/CORS/CSRF origins. |
| File upload | Polyglot/fake images, path traversal, EXIF/geolocation leak, public photo URL. | Pillow verifies actual format, JPEG/PNG whitelist, size/pixel limits, safe UUID object key, EXIF stripping, local private storage boundary, no `object_key` or permanent public URL in API, path traversal tests. |
| Rate limits | Abuse of auth/AI endpoints. | Scoped throttles for auth, AI nutrition, fitness and wellbeing endpoints; shared cache/Redis required for production multi-instance deployment. |
| Password reset | Account enumeration and reset token leakage. | Generic request response, hashed DB token, expiry, single-use tokens, old token revocation on new issue. |
| Secrets | Secrets committed or weak production env. | `.env` ignored, `.env.example` contains local-only placeholders, settings read from env; new system checks block weak production secret and dangerous production settings. |
| Logs | Sensitive data in logs. | Current app logging is minimal; Celery task payload excludes photo/object key/health data. Remaining work: structured redaction middleware/filter before production observability. |
| Django Admin | Excessive staff access or audit tampering. | Staff-only admin, token models not registered, dangerous bulk actions disabled, read-only sanitized `AdminAuditLog`, role-based model visibility tests. |
| Signed URLs | Long-lived public access to photos. | Current API does not issue signed URLs. Future signed URLs must be short-lived, owner-authorized and audited. |
| Object storage | Public buckets or object-key disclosure. | `PrivateObjectStorage` boundary; local MVP storage uses safe permissions and API hides keys. Production S3-compatible private backend still required. |
| Containers | Running as root, exposed internal ports. | Backend/Vision run as non-root `foodai`; PostgreSQL/Redis/Vision/Celery are not published to host by default. Remaining work: image digest pinning, read-only FS/capabilities/resource limits. |
| Dependencies | Vulnerable packages, poisoned registry/model weights. | Version ranges are constrained; Vision model revision is pinned; new Dependabot config monitors Python, frontend, GitHub Actions and Docker dependencies. Remaining work: vulnerability audit gate and lock strategy for backend. |
| Debug/security headers | Debug leakage, clickjacking, MIME sniffing, missing HTTPS headers. | Production settings now enable secure cookies, HSTS, HTTPS redirect, nosniff, referrer policy, COOP and frame denial; new system checks reject dangerous production config. |
| AI safety/privacy | Over-sharing user data to AI provider or unsafe advice. | Provider abstractions, minimal structured context, safety layers, consent-based message storage, no medical diagnosis/treatment positioning. |

## Remaining Risks / Оставшиеся риски

- Нет утверждения о полной безопасности; перед production нужен внешний security review/pentest.
- Production S3-compatible private storage backend ещё не реализован; local storage подходит только для
  разработки или явно контролируемого private volume.
- CSP пока не включён, потому что нужно отдельно протестировать Swagger/Admin/frontend interactions.
- Backend Python dependencies не имеют lock-файла; Dependabot добавлен, но vulnerability audit gate
  (`pip-audit`/аналог) требует отдельного решения, чтобы не ломать CI transient registry-сбоями.
- Docker base images и PyTorch/Hugging Face supply chain требуют регулярной проверки, digest pinning
  и provenance review перед production.
- Structured logging/redaction policy ещё foundation-level; перед production нужно добавить фильтры
  секретов/токенов и проверить observability pipeline.
- Service-to-service authentication для Vision пока отсутствует; Docker network boundary достаточен
  только для local/dev foundation.
- Legal/privacy review для стран запуска не проведён.
- Backup, disaster recovery, incident response и breach notification process пока не реализованы.

