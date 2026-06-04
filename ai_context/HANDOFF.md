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

## Latest Passing Command

```bash
cd /home/zzd/EmbedVerify
echo 1 | sudo -S env PYTHONPATH=src python3 -m embedverify.cli.main run suites/usb_smoke.yaml
```

## Latest Passing Reports

```text
/home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed/report.json
/home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed/report.txt
/home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed/outputs/
```

Latest validated commit:

```text
d268457 Improve CSI camera diagnostics
```

Latest result summary:

```text
report_status: passed
board: recomputer_j401
Function result status fields: none
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

Implemented but not yet all passing on current hardware configuration:

```text
suite: suites/connected_peripherals_smoke.yaml
cases: wireless_basic, display_hdmi, csi_camera, uart_loopback
functions:
  wifi.detect / wifi.scan
  bluetooth.detect / bluetooth.scan
  display.detect
  camera.detect / camera.capture_smoke
  uart.list_ports / uart.loopback
```

Latest Jetson run:

```text
request_id: 31439b6282bf
status: failed
report: /tmp/embedverify-connected-reports/20260604T044600Z_31439b6282bf_failed/report.json
```

Passing portions:

```text
wifi.scan: 54 networks
bluetooth.scan: 62 devices
display.detect: subsystem_present=true, hdmi_audio_input_count=4
```

Current blockers:

```text
CSI: Argus provider unavailable / camera not available. Do not automate
jetson-io.py inside Function. User should manually select the correct CSI
camera overlay using jetson-io.py, reboot, then rerun csi_camera.

UART: auto loopback tested /dev/ttyTHS1 and /dev/ttyTHS2; neither received the
payload. User should confirm the exact J401 header UART pins and pinmux/device
mapping before rerunning with a port override.
```

Regression after these code changes:

```text
usb_smoke passed:
/tmp/embedverify-regression-reports/20260604T044728Z_5f2b1735a238_passed/report.json

peripheral_smoke passed:
/tmp/embedverify-regression-reports/20260604T044728Z_9380cade707a_passed/report.json
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
