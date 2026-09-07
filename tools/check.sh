#!/usr/bin/env bash
# Single entry point wiring the build and every verification step together.
#
#   tools/check.sh              # build (online) + verify + no-fork guard
#   tools/check.sh --offline    # reuse whatever is already cached, still verifies checksums
#   tools/check.sh --no-build   # skip the build step, verify whatever is already at dist/darq
#
# The build step produces both dist/darq and dist/install.sh; the verify step checks both.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BUILD_ARGS=()
DO_BUILD=1
for arg in "$@"; do
  case "$arg" in
    --offline) BUILD_ARGS+=("--offline") ;;
    --no-build) DO_BUILD=0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

echo "== unit tests =="
PYTHONPATH="$ROOT_DIR" python3 -m unittest discover -s tests -q

echo
echo "== check_no_engine_code.py =="
python3 tools/check_no_engine_code.py

if [ "$DO_BUILD" -eq 1 ]; then
  echo
  echo "== build_darq.py =="
  python3 tools/build_darq.py "${BUILD_ARGS[@]}"
fi

echo
echo "== verify_darq.py =="
python3 tools/verify_darq.py

echo
echo "All checks passed."
