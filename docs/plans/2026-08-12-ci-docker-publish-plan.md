# CI Docker Publishing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build Docker images on pull requests and publish `latest` plus short-SHA tags to this repository's GHCR package after successful pushes to `main`.

**Architecture:** Extend the existing CI workflow with separate gated build and publish jobs rather than creating an independent workflow. The pull-request job has read-only permissions; only the `main` publish job receives package write access. Use the official Docker GitHub Actions for metadata, registry login, BuildKit caching, build, and push.

**Tech Stack:** GitHub Actions, Docker Buildx, GHCR, Just

---

### Task 1: Prove the missing CI contract

**Files:**
- Inspect: `.github/workflows/ci.yml`
- Inspect: `justfile`

**Step 1: Run failing contract assertions**

Assert that the workflow contains a Docker job publishing to
`ghcr.io/${{ github.repository }}`, and that the Justfile has no
`push-gitdocker` recipes.

**Step 2: Verify RED**

Expected: the workflow assertion fails because no Docker job exists, and the
Justfile assertion fails because both manual publishing recipes exist.

### Task 2: Add gated Docker build and publishing

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Add separate Docker jobs**

Make both depend on `secrets`, `lint`, and `test`. Build pull requests with
read-only permissions and without push. On pushes to `main`, authenticate to GHCR
with package write permission and publish `latest` and the seven-character
commit SHA to `ghcr.io/${{ github.repository }}`.

**Step 2: Add BuildKit caching and repository labels**

Use GitHub Actions cache storage and Docker metadata outputs.

### Task 3: Remove manual publishing and update instructions

**Files:**
- Modify: `justfile`
- Modify: `AGENTS.md`

**Step 1: Remove obsolete recipes**

Delete `push-gitdocker` and `push-gitdocker-full`, preserving local Docker
build and run recipes.

**Step 2: Update repository guidance**

Replace the mandatory local post-push command with the CI publishing contract
and the new GHCR image coordinates.

### Task 4: Verify

**Files:**
- Modify: `docs/exec-plans/active/2026-08-12-ci-docker-publish.md`

**Step 1: Run static contract checks**

Parse the workflow YAML, validate the Justfile, and rerun the contract
assertions.

**Step 2: Build the Docker image locally**

Run a local Docker build with the commit build argument.

**Step 3: Run project checks**

Run formatting, lint, type checks, tests, and secret scanning.

**Step 4: Complete the execution plan**

Mark all checklist items complete and move it to `docs/exec-plans/completed/`.
