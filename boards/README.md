# Board Profiles

Board profiles declare resources and choose capability implementations. They do
not define test flow. Suites and cases stay board-neutral and call stable
Functions such as `usb.detect`, `storage.info`, or `camera.capture_smoke`.

## Selection Rules

Board selection priority is:

```text
CLI --board > root config.yaml > error
```

Do not bind a normal suite to one board. Keep board choice in `config.yaml` or
the CLI so the same suite can run on Jetson, RK, or later platforms.

## Profile Shape

```yaml
name: recomputer_j401
platform: linux
adapter: jetson
capabilities:
  usb: linux_generic
  storage: linux_generic
  camera: linux_generic
  system_info: jetson
interfaces:
  usb:
    items:
      - usb_host_0
tools_required:
  - lsusb
metadata:
  vendor: Seeed
  family: Jetson
```

## Capability Rules

- The key under `capabilities` is the Function-facing capability name.
- The value is the implementation selected by the board.
- Prefer `linux_generic` for portable Linux command/sysfs behavior.
- Use platform adapters such as `jetson` or `rk` only when behavior is
  platform-specific.
- Function output must stay stable across boards:

```json
{
  "code": 0,
  "message": "...",
  "details": {},
  "metrics": {}
}
```

## Adding A Board

1. Create `boards/<board_name>.yaml`.
2. Start with generic capabilities that already exist.
3. Add interface names that describe board resources, not Linux implementation
   details only.
4. Add required tools so target bootstrap checks are explicit.
5. Run at least dry-run first:

```bash
PYTHONPATH=src python3 -m embedverify.cli.main run suites/peripheral_smoke.yaml --board <board_name> --dry-run
```

6. Run the smallest real case before running broad suites.

## When To Add A New Capability Implementation

Add a new implementation only when the board cannot use an existing capability
without board-specific command branches. For example:

```text
good: camera: linux_generic
good: system_info: jetson
good: system_info: rk
avoid: Fixture decides whether camera commands are Jetson or RK commands
```

The dispatch point is the capability registry, not a Fixture layer.
