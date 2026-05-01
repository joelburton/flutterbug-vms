# flutterbug-vms

Native binaries of seven interactive-fiction VMs (glulxe, git, bocfel, bocfel-noz6, hugo, scare, tads), all linked against [RemGlk-rs](https://github.com/curiousdannii/remglk-rs) and speaking the same RemGlk JSON protocol over stdin/stdout that emglken's wasm builds use. Built specifically to let [flutterbug](https://github.com/joelburton/flutterbug) consume IF VMs without bundling Node + WebAssembly.

This is a personal repo. The hard work — tracking each VM's submodule, source list, and compile flags — is all done by [emglken](https://github.com/curiousdannii/emglken), which is included here as a submodule. This repo just adds a parallel CMake setup that builds for the host triple instead of `wasm32-unknown-emscripten`, plus a small Python wrapper.

## Build

```bash
git clone --recurse-submodules https://github.com/joelburton/flutterbug-vms.git
cd flutterbug-vms
./build.sh
```

`build.sh` does three things: applies a small patch to remglk-rs (see `patches/`), runs `cargo build --release -p remglk_capi`, and runs `cmake --build`. The seven binaries land in `build/`.

Requirements: Rust toolchain (1.80+), CMake 3.13+, a C/C++ compiler, and zlib (for scare).

## Run

```bash
# Auto-detect VM by file extension, cheap terminal mode
python -m flutterbug_vms.cli path/to/story.ulx

# Same, but expose RemGlk JSON over stdio for programmatic consumers
python -m flutterbug_vms.cli --rem path/to/story.ulx

# Force a specific VM (e.g. force git instead of glulxe)
python -m flutterbug_vms.cli --vm git path/to/story.ulx

# Or invoke a binary directly — it's just a normal RemGlk-stdio program
./build/glulxe path/to/story.ulx
```

## Library use from Python

```python
from flutterbug_vms import VMRunner

with VMRunner("story.ulx") as vm:
    vm.send({"type": "init", "gen": 0,
             "metrics": {"width": 80, "height": 50},
             "support": ["timer"]})
    update = vm.recv()
    vm.send({"type": "line", "gen": 1, "window": 1, "value": "look"})
    update = vm.recv()
```

## Patches

`patches/remglk-rs-window-arrangement-lock.patch` fixes a `try_lock` deadlock in `glk_window_set_arrangement` that bocfel triggers on startup. The bug exists upstream but is masked by emscripten's mutex semantics in the wasm builds. Once it's PR'd and merged into curiousdannii/remglk-rs, this patch can be dropped.

## Limitations

- macOS/Linux only at the moment. Windows builds should work in theory (no platform-specific code), but untested.
- No prebuilt wheels yet. You build from source.
- The cheap-console mode is just a renderer for development / smoke testing — it doesn't try to be a polished terminal IF interpreter. For real terminal play, use the actual binaries with the `--rem` mode and a smarter front-end, or use one of the dedicated terminal interpreters.
