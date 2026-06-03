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
/home/zzd/EmbedVerify/reports/84ee0070f16d_passed.json
/home/zzd/EmbedVerify/reports/84ee0070f16d_passed.txt
```

Latest validated commit:

```text
b6cc509 Split USB and storage functions into entrypoint modules
```

Latest result summary:

```text
report_status: passed
board: recomputer_j401
Function result status fields: none
read_speed_mbps: 162.0
write_speed_mbps: 17.7
```

## Notes

- USB storage auto-discovery found `/dev/sda`.
- Auto-mount used `/mnt/embedverify-sda1`.
- The mount was automatically removed after write speed testing.

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
