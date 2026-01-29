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


push-gitdocker tag="latest":
    # Build with fresh code (keeps dependency cache) and push
    docker build --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) \
                 --build-arg CACHEBUST=$(git rev-parse HEAD) \
                 -t {{IMAGE_NAME}}:{{tag}} .
    docker tag {{IMAGE_NAME}} ghcr.io/montelibero/{{IMAGE_NAME}}:{{tag}}
    docker push ghcr.io/montelibero/{{IMAGE_NAME}}:{{tag}}

push-gitdocker-full tag="latest":
    # Full rebuild without any cache and push
    docker build --no-cache --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) -t {{IMAGE_NAME}}:{{tag}} .
    docker tag {{IMAGE_NAME}} ghcr.io/montelibero/{{IMAGE_NAME}}:{{tag}}
    docker push ghcr.io/montelibero/{{IMAGE_NAME}}:{{tag}}

test:
    uv run pytest