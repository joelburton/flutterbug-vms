#!/usr/bin/env bash
# Build all native VMs.
# 1. Apply local patches to submodules (idempotent: skipped if already applied)
# 2. cargo build remglk_capi natively
# 3. cmake configure + build
set -euo pipefail
cd "$(dirname "$0")"

# Patches applied to vendored submodules. Each entry is "submodule:patch".
# Patches are idempotent: skipped if already applied.
PATCHES=(
    "emglken/remglk:patches/remglk-rs-window-arrangement-lock.patch"
    "emglken/remglk:patches/remglk-rs-c-char-signedness.patch"
    "emglken/remglk:patches/remglk-rs-msvc-unreachable.patch"
    "emglken/hugo:patches/hugo-undef-win32.patch"
    "emglken/garglk:patches/scare-undef-win32.patch"
)

for entry in "${PATCHES[@]}"; do
    SUBMODULE="${entry%%:*}"
    PATCH="${entry#*:}"
    # Path to patch from inside the submodule directory.
    REL_PATCH="$(python3 -c "import os; print(os.path.relpath('$PATCH', '$SUBMODULE'))")"
    if ! git -C "$SUBMODULE" apply --reverse --check "$REL_PATCH" >/dev/null 2>&1; then
        echo "Applying $PATCH to $SUBMODULE"
        git -C "$SUBMODULE" apply "$REL_PATCH"
    else
        echo "$PATCH already applied"
    fi
done

# On Git Bash for Windows (MSYSTEM is set), /usr/bin/link.exe (a GNU
# coreutils utility — *not* a linker) shadows MSVC's link.exe in PATH.
# Move MSVC's bin dir to the front so every PATH lookup (cargo,
# ninja, cl.exe, link.exe) resolves to the right tools.
if [[ -n "${MSYSTEM:-}" && -n "${VCToolsInstallDir:-}" ]]; then
    MSVC_BIN_UNIX=$(cygpath -u "${VCToolsInstallDir}bin\\Hostx64\\x64" 2>/dev/null || true)
    if [[ -n "$MSVC_BIN_UNIX" ]]; then
        export PATH="$MSVC_BIN_UNIX:$PATH"
        echo "Prepended MSVC bin to PATH: $MSVC_BIN_UNIX"
    fi
fi

(cd emglken && cargo build --release -p remglk_capi)

# On Windows, prefer Ninja so output lands flat in build/ (instead of build/Release/).
CMAKE_FLAGS=()
if [[ -n "${MSYSTEM:-}" ]]; then
    CMAKE_FLAGS+=(-G Ninja)
fi

# `${arr[@]+"${arr[@]}"}` is the "expand if set, else nothing" idiom that
# survives `set -u` on bash 3.2 (macOS) when the array is empty.
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release ${CMAKE_FLAGS[@]+"${CMAKE_FLAGS[@]}"}
cmake --build build -j

echo
echo "Built binaries in build/:"
ls build | grep -v -E '^(CMake|cmake|Makefile|.*\.(a|lib|exp|pdb|ninja)$|build\.ninja|\.)' || true
