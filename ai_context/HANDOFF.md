# Handoff

## GitHub

```text
repo: https://github.com/Bohrium332/EmbedVerify
branch: main
latest known commit: 7b28f2b Use config board selection and code-only function results
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
7b28f2b Use config board selection and code-only function results
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
