#!/usr/bin/env bash
# Build all native VMs.
# 1. Apply local patches to submodules (idempotent: skipped if already applied)
# 2. cargo build remglk_capi natively
# 3. cmake configure + build
set -euo pipefail
cd "$(dirname "$0")"

REMGLK_DIR="emglken/remglk"
PATCH="patches/remglk-rs-window-arrangement-lock.patch"
if ! git -C "$REMGLK_DIR" apply --reverse --check "../../$PATCH" >/dev/null 2>&1; then
    echo "Applying $PATCH"
    git -C "$REMGLK_DIR" apply "../../$PATCH"
else
    echo "$PATCH already applied"
fi

(cd emglken && cargo build --release -p remglk_capi)

cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build -j

echo
echo "Built binaries in build/:"
ls build | grep -v -E '^(CMake|cmake|Makefile|.*\.a$)'
