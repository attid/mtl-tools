# CI Docker Publishing Design

## Context

Docker images are currently built and pushed from a developer workstation with
`just push-gitdocker`. That command publishes to the unrelated
`ghcr.io/montelibero/skynet` package and makes deployment depend on a manual
post-push step.

## Design

The existing GitHub Actions CI workflow gains separate Docker build and publish
jobs that depend on the secret scan, lint/type checks, and test jobs. This keeps
image publication behind the same quality gates as the source code while giving
pull requests read-only permissions.

- Pull requests build the Docker image with `contents: read` and without
  publishing it.
- Pushes to `main` publish the image to `ghcr.io/attid/skynet_bot`.
- Each published image receives `latest` and the seven-character commit SHA as
  tags.
- Only the publish job authenticates with the repository-scoped `GITHUB_TOKEN`
  and requests `packages: write`.
- GitHub Actions cache storage is used for BuildKit layers.
- OCI labels link the container package to this repository.

The local `build`, `build-fresh`, and `run` recipes remain available. Only the
manual GHCR publishing recipes are removed.

## Failure Behavior

If any prerequisite CI job fails, neither Docker job runs. A Docker build failure
blocks publication. Pull requests never receive package write permission, log in
to GHCR, or push, including pull requests from forks.

## Verification

Static assertions verify the workflow contract and absence of the obsolete
publishing recipes. The workflow YAML is parsed, `just --list` validates the
Justfile, and a local Docker build validates the Dockerfile path used by CI.
