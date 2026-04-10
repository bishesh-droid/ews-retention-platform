# CI/CD Documentation

## Database Migration Verification

When adding or modifying Alembic migrations, the following verification must pass in CI:

### Alembic Round-Trip Test

```bash
# 1. Upgrade to latest
alembic upgrade head

# 2. Downgrade one revision
alembic downgrade -1

# 3. Re-upgrade to verify reversibility
alembic upgrade head
```

Run this in CI on every migration file change to ensure migrations are reversible and don't corrupt data.

## Smoke Testing

After deployment, run the smoke test script:

```bash
cd scripts
chmod +x smoke_test.sh
./smoke_test.sh
```

Environment variables:
- `BASE_URL` - API base URL (default: http://localhost:8000)
- `SMOKE_TEST_USER` - Test user username (default: dev_admin)
- `SMOKE_TEST_PASS` - Test user password (default: changeme_local_only)

## Docker Build Verification

```bash
docker build -f docker/Dockerfile -t ews-platform .
docker run -p 8000:8000 ews-platform
```

## Feature Flags

The following feature flags control optional functionality:

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_CALENDAR_SCORER` | `true` | Enable calendar-aware risk scoring |
| `ENABLE_LLM_FEATURES` | `true` | Enable LLM-powered suggestions |

Set to `false` in `.env` to disable features without code changes.
