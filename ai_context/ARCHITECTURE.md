# Architecture

EmbedVerify uses four layers:

```text
Suite/Fixture -> Case -> Function -> Capability/Lib
```

## Suite / Fixture

Owns scenario orchestration only.

It defines which cases run and in what execution mode. It must not select board
logic. New configs should not contain `board`.

## Case

Owns function ordering and pass/fail rules.

Case configs call functions and define `expect.rules`. Business thresholds live
in Case or board-derived config, not inside low-level libraries.

## Function

Owns one stable test operation and returns the framework contract.

Function entrypoints should call module-local `*_lib.py` helpers, then assemble
the standard return structure.

Target layout:

```text
src/embedverify/functions/usb/
├── usb_lib.py
└── detect.py

src/embedverify/functions/storage/
├── storage_lib.py
├── info.py
├── read_speed.py
└── write_speed.py
```

Case names map to entrypoint modules:

```text
usb.detect -> embedverify.functions.usb.detect:execute
storage.read_speed -> embedverify.functions.storage.read_speed:execute
```

## Capability / Lib

Owns platform-specific command execution and parsing.

Generic Linux capability can be reused across Jetson and RK for USB/storage.
Platform-specific capability is reserved for system info, thermal, GPU/NPU, and
vendor-specific sysfs paths.

## Board Profile

Owns board resources and capability implementation choices.

Example:

```yaml
name: recomputer_j401
platform: linux
adapter: jetson
capabilities:
  usb: linux_generic
  storage: linux_generic
  system_info: jetson
```

