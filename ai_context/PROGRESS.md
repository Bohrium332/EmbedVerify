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
device: /dev/sda
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

## Next Round

- Sync latest storage safety changes to Jetson.
- Verify the dirty SSD path returns a controlled failure before mounting or
  writing.
- Ask the user whether to repair `/dev/sda1` or swap in a clean test disk.

## Round After Next

- After clean media is available, rerun full `suites/usb_smoke.yaml`.
- Add `skip_on_fail`.
- Add `label` / `save_output`.
- Add `{{...}}` template references.
- Change reports to timestamped report directories.
