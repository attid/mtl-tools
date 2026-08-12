IMAGE_NAME := "skynet"

# Default target
default:
    @just --list

# Docker targets
build tag="latest":
    # Build Docker image (uses cache)
    docker build --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) -t {{IMAGE_NAME}}:{{tag}} .

build-fresh tag="latest":
    # Build Docker image, force refresh source code but keep dependency cache
    docker build --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) \
                 --build-arg CACHEBUST=$(git rev-parse HEAD) \
                 -t {{IMAGE_NAME}}:{{tag}} .

run: test
    # Build and Run Docker container
    docker build --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) -t {{IMAGE_NAME}}:local .
    docker run --rm -p 8081:80 {{IMAGE_NAME}}:local



shell:
    # Open a shell into the running container
    docker-compose exec {{IMAGE_NAME}} sh

# Cleanup targets


clean-docker:
    # Clean up Docker images and containers
    docker system prune -f
    docker volume prune -f


lint:
    uv run --group dev ruff check .

format:
    uv run --group dev ruff format .

types:
    uv run --group dev pyright

test:
    uv run --group dev pytest

test-fast:
    uv run --group dev pytest tests --ignore=tests/routers

test-router:
    uv run --group dev pytest tests/routers

secrets:
    # Scan for leaked secrets (requires gitleaks: https://github.com/gitleaks/gitleaks)
    if command -v gitleaks >/dev/null 2>&1; then \
        gitleaks detect --source . -v; \
    else \
        docker run --rm -v "$PWD:/src" zricethezav/gitleaks detect --source /src -v; \
    fi
