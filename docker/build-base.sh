#!/usr/bin/env bash
# Build the django-whiteneuron base images (Alpine + Debian) from a git ref of this repo.
# Used as-is by .github/workflows/docker-base.yml, so local and CI builds are the same.
#
#   bash docker/build-base.sh                       # HEAD, load into the local docker
#   GIT_REF=v0.4.0.0 bash docker/build-base.sh      # a tag / branch / commit
#   GIT_REF=v0.4.0.0 bash docker/push-base.sh       # push with provenance + SBOM
#   VARIANTS=alpine bash docker/build-base.sh       # one variant (alpine | debian)
#
# Images: ${IMAGE_NAMESPACE}/django-whiteneuron-{alpine,debian}:v<pyproject version at GIT_REF>
#
# - Source: `git archive` of GIT_REF (never local files such as db.sqlite3, dist/, node_modules).
# - Dependencies: pinned from that ref's uv.lock (`uv export`), the set CI tests.
# - Dockerfiles / .dockerignore: this working copy, so older tags build too.
# - Pushing requires GIT_REF to be the release tag v<version>, so a published tag is
#   never overwritten with other code, and a clean docker/ directory.
#
# Requires: git, uv, docker buildx.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-anhneuron}"
# WN_-prefixed: python images (devcontainers, CI runners) export their own PYTHON_VERSION
WN_PYTHON_VERSION="${WN_PYTHON_VERSION:-3.13}"
WN_PLATFORM="${WN_PLATFORM:-linux/amd64}"
GIT_REF="${GIT_REF:-HEAD}"
PUSH="${PUSH:-0}"
VARIANTS="${VARIANTS:-alpine debian}"

die() { printf 'error: %b\n' "$*" >&2; exit 1; }

for variant in $VARIANTS; do
	case "$variant" in alpine|debian) ;; *) die "unknown variant '$variant' (alpine | debian)" ;; esac
done
command -v uv >/dev/null || die "uv is required (https://docs.astral.sh/uv/)"

COMMIT="$(git -C "$ROOT_DIR" rev-parse --verify --quiet "${GIT_REF}^{commit}")" || die "unknown GIT_REF: ${GIT_REF}"
REF_VERSION="$(git -C "$ROOT_DIR" show "${COMMIT}:pyproject.toml" | sed -n 's/^version *= *"\(.*\)"/\1/p' | head -1)"
[ -n "$REF_VERSION" ] || die "no version in pyproject.toml at ${GIT_REF}"
TAG="v${REF_VERSION}"

dirty_docker="$(git -C "$ROOT_DIR" status --porcelain -- docker .dockerignore)"
if [ "$PUSH" = "1" ]; then
	# A published image must be exactly the released code
	TAG_COMMIT="$(git -C "$ROOT_DIR" rev-parse --verify --quiet "refs/tags/${TAG}^{commit}")" \
		|| die "tag ${TAG} does not exist: tag the release before pushing its images"
	[ "$TAG_COMMIT" = "$COMMIT" ] \
		|| die "${GIT_REF} (${COMMIT:0:9}) is not the release tag ${TAG} (${TAG_COMMIT:0:9}); push with GIT_REF=${TAG}"
	[ -z "$dirty_docker" ] || die "uncommitted changes in docker/ or .dockerignore:\n${dirty_docker}"
else
	[ -z "$dirty_docker" ] || echo "warning: building with uncommitted changes in docker/ or .dockerignore" >&2
	if [ "$GIT_REF" = "HEAD" ] && [ -n "$(git -C "$ROOT_DIR" status --porcelain -- whiteneuron pyproject.toml uv.lock)" ]; then
		echo "warning: uncommitted changes under whiteneuron/, pyproject.toml or uv.lock are NOT included (building HEAD)" >&2
	fi
fi

CONTEXT_DIR="$(mktemp -d)"
trap 'rm -rf "$CONTEXT_DIR"' EXIT
git -C "$ROOT_DIR" archive --format=tar "$COMMIT" | tar -x -C "$CONTEXT_DIR"
cp "${ROOT_DIR}/.dockerignore" "$CONTEXT_DIR/.dockerignore"
[ -f "$CONTEXT_DIR/uv.lock" ] || die "no uv.lock at ${GIT_REF}"
(cd "$CONTEXT_DIR" && uv export --frozen --no-dev --no-emit-project --no-hashes \
	--format requirements-txt --quiet --output-file docker-requirements.txt)

BUILDER_ARGS=()
if [ "$PUSH" = "1" ]; then
	# Attestations need a BuildKit container builder (the plain "docker" driver can't on
	# the classic image store). CI (setup-buildx-action) already runs one.
	if docker buildx inspect 2>/dev/null | grep -qE '^Driver: +docker$'; then
		docker buildx inspect wn-base >/dev/null 2>&1 || docker buildx create --name wn-base --driver docker-container >/dev/null
		BUILDER_ARGS=(--builder wn-base)
	fi
	OUTPUT=(--provenance=mode=max --sbom=true --push)
	echo "==> Building and pushing base images ${TAG} (${COMMIT:0:9})..."
else
	OUTPUT=(--load)
	echo "==> Building base images ${TAG} from ${GIT_REF} (${COMMIT:0:9}, local only)..."
fi

for variant in $VARIANTS; do
	image="${IMAGE_NAMESPACE}/django-whiteneuron-${variant}:${TAG}"
	docker buildx build "${BUILDER_ARGS[@]}" \
		--platform "${WN_PLATFORM}" \
		--file "${SCRIPT_DIR}/Dockerfile.base-${variant}" \
		--build-arg "PYTHON_VERSION=${WN_PYTHON_VERSION}" \
		--build-arg "WHITENEURON_VERSION=${TAG}" \
		--label "org.opencontainers.image.revision=${COMMIT}" \
		--tag "$image" \
		--pull \
		"${OUTPUT[@]}" \
		"$CONTEXT_DIR"
	echo "==> ${image}"
done

echo "==> Base images ready."
