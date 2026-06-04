# Board Porting Guide

## Goal

Add new boards without changing Function output or suite semantics. Board
differences are handled by capability selection.

## Stable Contract

Every Function returns:

```json
{
  "code": 0,
  "message": "...",
  "details": {},
  "metrics": {}
}
```

Do not add `status` back to Function results.

## Porting Steps

1. Add a board YAML under `boards/`.
2. Select existing capabilities first.
3. Record required external fixtures for cases that need wiring or attached
   peripherals.
4. Run dry-runs for target suites.
5. Run one case at a time on hardware.
6. Only add a new capability implementation after proving `linux_generic`
   cannot model the board safely.

Verification order:

```text
board YAML parses
-> suite dry-run
-> one read-only case on hardware
-> one attached-device case on hardware
-> broader suite
```

Do not start by cloning an existing board-specific suite. Suite semantics should
stay portable unless the physical workflow is different.

## Capability Mapping

```text
usb          linux_generic
storage      linux_generic
network      linux_generic
pcie_nvme    linux_generic
rtc          linux_generic
fan          linux_generic
gpio         linux_generic
i2c          linux_generic
camera       linux_generic
wifi         linux_generic
bluetooth    linux_generic
display      linux_generic
uart         linux_generic
system_info  jetson | rk
```

Use `linux_generic` when the behavior can be expressed through stable Linux
commands, sysfs, or devfs paths. Use a platform-specific capability only when a
board family needs different commands, parsing, or safety checks.

Examples:

```text
good: wifi: linux_generic
good: display: linux_generic
good: system_info: jetson
good: system_info: rk
avoid: changing a Suite or Fixture to branch on board name
avoid: changing Function output fields for one platform
```

## Board YAML Checklist

Each board profile should answer these questions:

```text
name: stable CLI/config board id
platform: broad OS family, usually linux
adapter: board family, such as jetson or rk
capabilities: Function-facing capability -> implementation
interfaces: physical resources exposed by the board
tools_required: commands that must exist on the target
metadata: vendor/family/review notes
```

Interface names should describe hardware resources, not only Linux device
filenames. Use Linux device names only when they are part of the test contract
or the current board's expected discovery result.

## Case Scope Rules

- Required hardware should fail when missing.
- Optional hardware should be excluded from the suite until the fixture exists.
- Dangerous or persistent board configuration should be a documented manual
  precondition, not a normal Function side effect.
- Use standalone Case execution for uncertain hardware before adding the Case to
  a broad Suite.

## Jetson Notes

- CSI camera overlays are configured manually with `jetson-io.py`, followed by
  a reboot. Tests detect the configured result but do not mutate overlays.
- HDMI connector state may require an active local display manager session.
  The generic display capability tries sysfs and `xrandr` with common GDM
  Xauthority paths.
- UART loopback requires both correct RX/TX wiring and correct pinmux/device
  mapping.

## RK Notes

- Start with `usb`, `storage`, `network`, `gpio`, `i2c`, `uart`, `wifi`, and
  `bluetooth` as `linux_generic`.
- Add `system_info: rk` for SoC/vendor identification.
- Add RK-specific capabilities only when sysfs or vendor tools differ enough
  that a generic implementation would become unsafe or misleading.

## New Platform Acceptance

A new platform is ready for review when:

```text
board profile is committed
dry-run passes for the selected suite
at least one read-only case passes on hardware
attached-device cases document their external fixture assumptions
Function outputs still use code/message/details/metrics only
```
