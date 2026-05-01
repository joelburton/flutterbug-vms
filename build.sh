#!/usr/bin/env bash
# Build all native VMs.
# 1. Apply local patches to submodules (idempotent: skipped if already applied)
# 2. cargo build remglk_capi natively
# 3. cmake configure + build
set -euo pipefail
cd "$(dirname "$0")"

REMGLK_DIR="emglken/remglk"
PATCHES=(
    "patches/remglk-rs-window-arrangement-lock.patch"
    "patches/remglk-rs-c-char-signedness.patch"
)

for PATCH in "${PATCHES[@]}"; do
    if ! git -C "$REMGLK_DIR" apply --reverse --check "../../$PATCH" >/dev/null 2>&1; then
        echo "Applying $PATCH"
        git -C "$REMGLK_DIR" apply "../../$PATCH"
    else
        echo "$PATCH already applied"
    fi
done

(cd emglken && cargo build --release -p remglk_capi)

# On Windows, prefer Ninja so output lands flat in build/ instead of build/Release/.
CMAKE_FLAGS=()
case "${OSTYPE:-}" in
    msys*|cygwin*|win32) CMAKE_FLAGS+=(-G Ninja) ;;
esac

cmake -B build -S . -DCMAKE_BUILD_TYPE=Release "${CMAKE_FLAGS[@]}"
cmake --build build -j

echo
echo "Built binaries in build/:"
ls build | grep -v -E '^(CMake|cmake|Makefile|.*\.(a|lib|exp|pdb|ninja)$|build\.ninja)'
