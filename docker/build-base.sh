#!/usr/bin/env bash
# Build the django-whiteneuron base images (Alpine + Debian) from a git ref of this repo.
#
#   bash docker/build-base.sh                       # HEAD, load into the local docker
#   GIT_REF=v0.4.0.0 bash docker/build-base.sh      # a tag / branch / commit
#   PUSH=1 bash docker/build-base.sh                # push with provenance + SBOM (= push-base.sh)
#   VARIANTS=alpine bash docker/build-base.sh       # only one variant (alpine | debian)
#
# Images: ${IMAGE_NAMESPACE}/django-whiteneuron-{alpine,debian}:v<pyproject version>
# The release workflow (.github/workflows/docker-base.yml) does the same on every GitHub Release.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-anhneuron}"
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"
PLATFORM="${PLATFORM:-linux/amd64}"
GIT_REF="${GIT_REF:-HEAD}"
PUSH="${PUSH:-0}"
VARIANTS="${VARIANTS:-alpine debian}"

# Build from committed code only (no db.sqlite3, dist/, node_modules or local edits)
if ! git -C "$ROOT_DIR" rev-parse --verify --quiet "${GIT_REF}^{commit}" >/dev/null; then
	echo "Unknown GIT_REF: ${GIT_REF}" >&2
	exit 1
fi
if [ "$GIT_REF" = "HEAD" ] && [ -n "$(git -C "$ROOT_DIR" status --porcelain -- whiteneuron pyproject.toml)" ]; then
	echo "warning: uncommitted changes under whiteneuron/ or pyproject.toml are NOT included (building HEAD)" >&2
fi

# Tag = v<version> read from pyproject at that ref (override with WHITENEURON_VERSION)
REF_VERSION="$(git -C "$ROOT_DIR" show "${GIT_REF}:pyproject.toml" | sed -n 's/^version *= *"\(.*\)"/\1/p' | head -1)"
WHITENEURON_VERSION="${WHITENEURON_VERSION:-v${REF_VERSION}}"
if [ -z "$REF_VERSION" ]; then
	echo "Could not read the version from pyproject.toml at ${GIT_REF}" >&2
	exit 1
fi

if [ "$PUSH" = "1" ]; then
	OUTPUT=(--provenance=mode=max --sbom=true --push)
	echo "==> Building and pushing base images ${WHITENEURON_VERSION} from ${GIT_REF}..."
else
	OUTPUT=(--load)
	echo "==> Building base images ${WHITENEURON_VERSION} from ${GIT_REF} (local only)..."
fi

# Context = the tree at GIT_REF; Dockerfiles come from the working copy so older tags build too
CONTEXT_DIR="$(mktemp -d)"
trap 'rm -rf "$CONTEXT_DIR"' EXIT
git -C "$ROOT_DIR" archive --format=tar "$GIT_REF" | tar -x -C "$CONTEXT_DIR"
cp "${ROOT_DIR}/.dockerignore" "$CONTEXT_DIR/.dockerignore"

for variant in $VARIANTS; do
	case "$variant" in alpine|debian) ;; *) echo "Unknown variant: $variant" >&2; exit 1 ;; esac
	image="${IMAGE_NAMESPACE}/django-whiteneuron-${variant}:${WHITENEURON_VERSION}"
	docker buildx build \
		--platform "${PLATFORM}" \
		--file "${ROOT_DIR}/docker/Dockerfile.base-${variant}" \
		--build-arg "PYTHON_VERSION=${PYTHON_VERSION}" \
		--build-arg "WHITENEURON_VERSION=${WHITENEURON_VERSION}" \
		--tag "$image" \
		--pull \
		"${OUTPUT[@]}" \
		"$CONTEXT_DIR"
	echo "==> ${image}"
done

echo "==> Base images ready."
