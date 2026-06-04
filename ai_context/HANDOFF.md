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
b7e708d Document USB review chain completion
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
