# Handoff

## GitHub

```text
repo: https://github.com/Bohrium332/EmbedVerify
branch: main
latest known commit: run `git log --oneline -1`
```

## Verified Board

```text
host: 192.168.4.149
user: zzd
repo path: /home/zzd/EmbedVerify
proxy: 192.168.4.148:7890
```

The board is Jetson/Tegra, not RK:

```text
Linux zzd-desktop 5.15.185-tegra ... aarch64
```

## Latest Passing Commands

```bash
cd /home/zzd/EmbedVerify
echo 1 | sudo -S env PYTHONPATH=src python3 -m embedverify.cli.main run suites/connected_peripherals_smoke.yaml --reports-dir /tmp/embedverify-csi-hdmi-reports
echo 1 | sudo -S env PYTHONPATH=src python3 -m embedverify.cli.main run suites/peripheral_smoke.yaml --reports-dir /tmp/embedverify-regression-reports
echo 1 | sudo -S env PYTHONPATH=src python3 -m embedverify.cli.main run-case cases/uart_loopback.yaml --reports-dir /tmp/embedverify-uart-reports
```

## Latest Passing Reports

```text
/tmp/embedverify-csi-hdmi-reports/20260604T061819Z_e32936d76393_passed/report.json
/tmp/embedverify-regression-reports/20260604T062040Z_f2dc71838b8a_passed/report.json
/tmp/embedverify-uart-reports/20260604T082952Z_1d75e50916cb_passed/report.json

USB storage baseline, only valid when a USB mass-storage disk is attached:
/home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed/report.json
/home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed/report.txt
/home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed/outputs/
```

Latest validated code commit:

```text
f8a3833 Stabilize CSI and HDMI smoke checks
```

Latest result summary:

```text
board: recomputer_j401
Function result status fields: none

connected_peripherals_smoke: passed
wifi.scan: 82 networks
bluetooth.scan: 85 devices
display.detect: DP-1 connected primary 1024x600
camera.capture_smoke: capture_ok=true

peripheral_smoke: passed

uart_loopback standalone case: passed
uart port: /dev/ttyTHS1
uart payload: EVUART1
uart report: /tmp/embedverify-uart-reports/20260604T082952Z_1d75e50916cb_passed/report.json

USB storage baseline, from earlier run with USB storage attached:
USB storage: Realtek RTL9210 M.2 NVME Adapter
USB speed: 10G
storage layout: whole-disk ext4 on /dev/sda
storage.detect: passed
read_speed_mbps: 720.0
write_speed_mbps: 445.0
integrity_match: true
TXT report format: code=<value>, no Function status
labels/save_output/templates/report directories: verified
direct suite/case/function execution: verified
```

## Notes

- USB storage auto-discovery found `/dev/sda`.
- Current clean SSD uses whole-disk ext4 on `/dev/sda`.
- The mount was automatically removed after write speed testing.

## Peripheral Expansion In Progress

First-batch J401 carrier-board interfaces have been implemented locally:

```text
suite: suites/peripheral_smoke.yaml
cases: network_basic, nvme_storage, rtc_basic, fan_basic, gpio_basic, i2c_basic
functions:
  network.list_interfaces / network.link_status / network.ping
  pcie_nvme.detect
  rtc.list_devices / rtc.read
  fan.info
  gpio.list_chips / gpio.line_info
  i2c.list_buses / i2c.scan
```

Implementation remains in the current framework shape:

```text
Function output: code/message/details/metrics only
Board selection: CLI --board > config.yaml > error
Capability selection: Function calls capability registry, no Fixture board branching
```

Local verification passed:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m embedverify.cli.main run suites/peripheral_smoke.yaml --dry-run
```

Jetson verification passed:

```bash
cd /home/zzd/EmbedVerify
PYTHONPATH=src python3 -m unittest discover -s tests -v
echo 1 | sudo -S env PYTHONPATH=src python3 -m embedverify.cli.main run suites/peripheral_smoke.yaml --reports-dir /tmp/embedverify-peripheral-reports
echo 1 | sudo -S env PYTHONPATH=src python3 -m embedverify.cli.main run suites/usb_smoke.yaml --file-size-mb 1 --reports-dir /tmp/embedverify-usb-regression-reports
```

Latest peripheral report:

```text
/tmp/embedverify-peripheral-reports/20260604T034332Z_d5db47342266_passed/report.json
```

Latest USB regression report:

```text
/tmp/embedverify-usb-regression-reports/20260604T034358Z_fdf994422bb1_passed/report.json
```

## Connected Peripherals

Implemented and passing for the hardware the user currently wants in the suite:

```text
suite: suites/connected_peripherals_smoke.yaml
cases: wireless_basic, display_hdmi, csi_camera
functions:
  wifi.detect / wifi.scan
  bluetooth.detect / bluetooth.scan
  display.detect
  camera.detect / camera.capture_smoke
```

Latest Jetson run:

```text
request_id: e32936d76393
status: passed
report: /tmp/embedverify-csi-hdmi-reports/20260604T061819Z_e32936d76393_passed/report.json
```

Passing portions:

```text
wifi.detect: wlan0 detected
wifi.scan: 82 networks
bluetooth.detect: controller powered
bluetooth.scan: 85 devices
display.detect: DP-1 connected primary 1024x600, connected_count=1
camera.detect: NvArgus plugin available, /dev/media0, /dev/video0, /dev/video1
camera.capture_smoke: one-frame Argus capture passed
```

Current non-suite hardware notes:

```text
CSI: The user manually selected the camera overlay with jetson-io.py and
rebooted. Keep this as a manual precondition. Do not automate jetson-io.py
inside a normal Function.

UART: /dev/ttyTHS1 maps to Jetson Orin UART1 / 0x3100000.serial. Standalone
cases/uart_loopback.yaml passed with payload EVUART1. Keep it out of
connected_peripherals_smoke until the user re-approves adding UART back to the
default attached-device suite.

UART limitation: payloads of 1-7 bytes passed in the current setup; payloads of
8 bytes or more produced NUL-prefixed data. Treat this as a separate UART
stress/driver investigation, not the basic smoke signal.
```

Regression after CSI/HDMI stabilization:

```text
local unit tests: 38/38 passed
Jetson unit tests: 38/38 passed

peripheral_smoke passed:
/tmp/embedverify-regression-reports/20260604T062040Z_f2dc71838b8a_passed/report.json

usb_smoke failed only because no USB mass-storage disk was attached in the
current CSI/HDMI/Wi-Fi/BT setup:
/tmp/embedverify-regression-reports/20260604T061958Z_9eafba4d3382_failed/report.json
```

## Current SSD Caution

The user replaced the original USB flash drive with an SSD on 2026-06-03.
The SSD enumerated as `/dev/sda` over USB 10G/UAS and read speed was around
700 MB/s, but write testing triggered real kernel errors:

```text
uas reset
I/O error, dev sda
EXT4-fs error
Detected aborted journal
Remounting filesystem read-only
```

After reboot, `/dev/sda1` was unmounted but not clean:

```text
tune2fs: Filesystem state: clean with errors
tune2fs: Filesystem features includes needs_recovery
fsck -n: free blocks/inodes counts are wrong
```

Do not run full write smoke on this SSD until the user explicitly approves
repairing `/dev/sda1` or provides a clean test disk. The framework now blocks
auto-mount write testing for dirty ext filesystems and adds storage dmesg
diagnostics to write failures.

Verified guard behavior on Jetson:

```text
Function: storage.write_speed(mount_point="auto")
code: -1
message: USB storage filesystem is not clean; repair required before write test
filesystem_state: clean with errors
needs_recovery: true
mount/write attempted: no
```
