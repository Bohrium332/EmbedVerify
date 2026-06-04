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
3. Run dry-runs for target suites.
4. Run one case at a time on hardware.
5. Only add a new capability implementation after proving `linux_generic`
   cannot model the board safely.

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
