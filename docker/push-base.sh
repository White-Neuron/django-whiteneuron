#!/usr/bin/env bash
# Build and push the base images with provenance + SBOM. Same options as build-base.sh.
set -euo pipefail
PUSH=1 exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/build-base.sh" "$@"
