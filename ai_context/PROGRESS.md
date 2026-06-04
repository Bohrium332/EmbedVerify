# Progress

## Current Done

- Created platform-neutral EmbedVerify MVP repository.
- Pushed repository to `https://github.com/Bohrium332/EmbedVerify`.
- Implemented USB Host + USB storage smoke suite.
- Implemented generic Linux USB enumeration.
- Implemented USB storage auto-discovery.
- Implemented auto mount/unmount for write speed when running as root.
- Fixed USB device-level speed parsing from `lsusb -t`.
- Verified reComputer J401 / Jetson USB smoke on real hardware.
- Added AI handoff context in `CLAUDE.md`, `CODEX.md`, and `ai_context/`.
- Added root `config.yaml` board selection.
- Removed board binding from `suites/usb_smoke.yaml`.
- Removed `status` from Function return values.
- Updated USB Case expectations to use `code + metrics`.
- Verified config-driven USB smoke on real hardware without passing `--board`.
- Split `usb.py` and `storage.py` into entrypoint + `*_lib.py` layout.
- Added storage write diagnostics for timeout/failure paths.
- Added ext filesystem health guard before auto-mount write tests.
- Verified the dirty SSD guard path on Jetson.
- Added support for USB disks that have a filesystem directly on the disk node
  instead of a partition.
- Verified full USB smoke on the clean whole-disk ext4 SSD.
- Fixed TXT report formatting so Function results display `code=<value>`
  instead of the removed Function `status`.
- Added `label`, `skip_on_fail`, `save_output`, parameter templates, and
  timestamped report directories.
- Completed the USB review chain as an architecture sample, not as the final
  product scope.
- Added direct suite/case/function execution entries.
- Added `storage.detect` and `storage.integrity_check`.
- Added first-batch peripheral coverage for J401 carrier-board interfaces:
  `network`, `pcie_nvme`, `rtc`, `fan`, `gpio`, and `i2c`.
- Added `suites/peripheral_smoke.yaml` plus six read-only/low-risk cases:
  `network_basic`, `nvme_storage`, `rtc_basic`, `fan_basic`, `gpio_basic`,
  and `i2c_basic`.
- Added unit coverage for new peripheral Function entrypoints and generic Linux
  parsers.

## Latest Passing Metrics

```text
board: recomputer_j401
USB device: Realtek RTL9210 M.2 NVME Adapter
USB speed: 10G
storage layout: whole-disk ext4 on /dev/sda
read_speed_mbps: 720.0
write_speed_mbps: 445.0
integrity_match: true
latest report dir: /home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed
```

## Latest SSD Investigation

```text
date: 2026-06-03
previous device: /dev/sda1 on /dev/sda
transport: USB 10G, UAS
model: External
partition: /dev/sda1 ext4
state after reboot: unmounted
```

The SSD enumerates correctly on USB 10G/UAS. The previous write test produced
real kernel storage errors, including UAS resets, `/dev/sda` I/O errors,
EXT4 errors, aborted journal, and read-only remount.

After reboot, read-only checks showed:

```text
tune2fs: Filesystem state: clean with errors
tune2fs: Filesystem features includes needs_recovery
fsck -n: free blocks/inodes counts are wrong
```

Do not run write tests on this SSD partition until it is repaired with an
explicit user-approved fsck repair or replaced with a clean test disk.

The guarded `storage.write_speed(mount_point="auto")` path now returns before
mounting or writing:

```text
code: -1
message: USB storage filesystem is not clean; repair required before write test
filesystem_state: clean with errors
needs_recovery: true
```

## Current Clean SSD

```text
date: 2026-06-03
device: /dev/sda
layout: whole-disk ext4, no /dev/sda1 partition
model: RTL9210B-CG
USB link: 10G, UAS
tune2fs state: clean
```

Jetson `e2fsck 1.46.5` does not understand this filesystem's `FEATURE_C12`
and `FEATURE_R16`, so `fsck -n` cannot be used as the pass/fail signal for this
disk. The framework now supports whole-disk filesystems and uses `tune2fs`
`Filesystem state` for the pre-mount ext health guard.

Latest full smoke passed:

```text
request_id: ce9ef4515ed8
report_status: passed
usb.detect: code=0, 10G Realtek RTL9210 device detected
storage.detect: code=0, one USB disk detected
storage.info: code=0, whole_disk_filesystem=true
storage.read_speed: code=0, 720.0 MB/s
storage.write_speed: code=0, 445.0 MB/s
storage.integrity_check: code=0, integrity_match=true
report dir: /home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed
saved outputs: 6 function output JSON files
report text format: code=<value>, no Function status field
```

## Latest Peripheral Smoke

```text
date: 2026-06-04
board: recomputer_j401
suite: peripheral_smoke
request_id: d5db47342266
report_status: passed
report dir: /tmp/embedverify-peripheral-reports/20260604T034332Z_d5db47342266_passed
```

Passed functions:

```text
network.list_interfaces: 6 non-loopback interfaces found
network.link_status: eth0 up, 1000 Mbps, carrier=true
network.ping: gateway 192.168.4.2, 2/2 packets, avg 0.953 ms
pcie_nvme.detect: /dev/nvme0n1, 128 GB NVMe detected
rtc.list_devices: /dev/rtc, /dev/rtc0, /dev/rtc1 detected
rtc.read: hwclock read succeeded
fan.info: pwmfan + pwm_tach detected, max_rpm around 1723
gpio.list_chips: gpiochip0/gpiochip1 detected, 196 lines total
gpio.line_info: gpioinfo for /dev/gpiochip0 succeeded
i2c.list_buses: 7 buses detected
i2c.scan: bus 7 scan completed, 0 devices found
```

USB regression after peripheral changes also passed:

```text
suite: usb_smoke
request_id: fdf994422bb1
report_status: passed
report dir: /tmp/embedverify-usb-regression-reports/20260604T034358Z_fdf994422bb1_passed
file_size_mb: 1
usb storage: /dev/sda, Realtek RTL9210, 10G
integrity_match: true
auto mount cleanup: /mnt/embedverify-sda not mounted after run
```

## Next Round

- Push the verified peripheral commits after final local status checks.
- Keep USB as the regression baseline while expanding peripheral coverage.

## Round After Next

- Decide which second-batch interfaces have hardware attached: CAN/CAN FD,
  UART loopback, CSI camera, M.2 Key E Wi-Fi/BT, HDMI display, SPI/PWM/I2S.
