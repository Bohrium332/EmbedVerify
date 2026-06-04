# USB Review Chain

USB is currently used as the architecture review sample. It is not the final
project scope. The goal of this chain is to prove the framework layering,
board selection, Function contract, reporting, and direct execution entries.

## Verified Execution Levels

```bash
PYTHONPATH=src python3 -m embedverify.cli.main run-function storage.detect --params '{"expected_type":"disk","transport":"usb"}'
PYTHONPATH=src python3 -m embedverify.cli.main run-case cases/usb_host_storage.yaml --file-size-mb 16
PYTHONPATH=src python3 -m embedverify.cli.main run suites/usb_smoke.yaml --file-size-mb 16
```

All three levels were verified on the Jetson target.

## Verified Case Steps

| Order | Function | Purpose |
| --- | --- | --- |
| 1 | `usb.detect` | Enumerate USB devices and link speed. |
| 2 | `storage.detect` | Detect USB storage disks with `lsblk` filters. |
| 3 | `storage.info` | Collect block-device details and auto-discovery data. |
| 4 | `storage.read_speed` | Measure read speed from the discovered disk. |
| 5 | `storage.write_speed` | Auto-mount, write a temporary file, then unmount. |
| 6 | `storage.integrity_check` | Write random data, read it back, and compare hashes. |

## Latest Hardware Result

```text
board: recomputer_j401
device: Realtek RTL9210 M.2 NVME Adapter
USB link: 10G / UAS
storage: /dev/sda whole-disk ext4
suite request_id: ce9ef4515ed8
suite status: passed
report dir: /home/zzd/EmbedVerify/reports/20260604T023629Z_ce9ef4515ed8_passed
read_speed_mbps: 720.0
write_speed_mbps: 445.0
integrity_match: true
```

The run generated `report.json`, `report.txt`, and six saved Function output
JSON files under `outputs/`.

## Review Status

| Area | Status |
| --- | --- |
| Root `config.yaml` board selection | Done |
| CLI `--board` override priority | Done |
| Suite execution | Done |
| Case execution | Done |
| Function execution | Done |
| Function return without `status` | Done |
| Label/template/save_output/report directory | Done |
| USB storage dirty ext guard | Done |
| Whole-disk filesystem support | Done |
| Direct storage integrity check | Done |

## Known Follow-ups After Review

| Item | Reason |
| --- | --- |
| Broaden `storage.info` with UUID/blkid details | Original repo exposes richer storage identity data. |
| Decide next non-USB minimal chain | USB should now become a regression baseline. |
| Generalize capability contracts | Needed before adding more board families and modules. |
