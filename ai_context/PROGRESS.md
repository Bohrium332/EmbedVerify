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

## Latest Passing Metrics

```text
board: recomputer_j401
USB device: Kingston DataTraveler 3.0
USB speed: 5G
read_speed_mbps: 162.0
write_speed_mbps: 17.7
latest report: /home/zzd/EmbedVerify/reports/84ee0070f16d_passed.json
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

## Next Round

- Sync whole-disk filesystem support to Jetson.
- Run full `suites/usb_smoke.yaml` on the clean SSD.
- Inspect the generated JSON/TXT report and recent dmesg.

## Round After Next

- Add `skip_on_fail`.
- Add `label` / `save_output`.
- Add `{{...}}` template references.
- Change reports to timestamped report directories.
