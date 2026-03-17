# Docker Bootstrap Template

Generate `docker/` using this baseline.

Source of truth: `assets/docker/*.template` (copy, then patch variables).

## Required files

- `docker/Dockerfile`
- `docker/docker-compose.yml`
- `docker/docker-compose.deploy.yml`
- `docker/.env.docker`
- `docker/supervisord.conf`
- `docker/init.sh`
- `docker/start.sh` or `docker/start_daphne.sh`
- `docker/docker-build-and-run.sh`
- `docker/docker-start.sh`
- `docker/docker-stop.sh`
- `docker/docker-clear.sh`
- `docker/docker-destroy.sh`

## Compose topology by profile

- admin-core:
  - web service first
  - add db in staging/prod
- catalog-api:
  - db + web by default
- portal-cms:
  - web by default
  - db optional (enabled for production-like deployments)
  - async stack expected by default

## Build/runtime conventions

- Install Python deps with `uv sync --no-dev`.
- Run static collection as part of image build when applicable.
- Use non-root user for container runtime.
- Mount `.env.docker` and `media/`.
- Keep local restart policy conservative (`no`).
- Mark copied shell scripts executable (`chmod +x docker/*.sh`).

## Validation

- `docker compose -f docker/docker-compose.yml config`
- `docker compose -f docker/docker-compose.yml up -d --build`
- Check web endpoint health.
