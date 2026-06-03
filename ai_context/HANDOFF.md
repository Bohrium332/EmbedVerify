# Handoff

## GitHub

```text
repo: https://github.com/Bohrium332/EmbedVerify
branch: main
latest known commit: 16a3b78 Auto-discover USB storage for smoke tests
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
echo 1 | sudo -S env PYTHONPATH=src python3 -m embedverify.cli.main run suites/usb_smoke.yaml --board recomputer_j401
```

## Latest Passing Reports

```text
/home/zzd/EmbedVerify/reports/fcc6621080f9_passed.json
/home/zzd/EmbedVerify/reports/fcc6621080f9_passed.txt
```

## Notes

- USB storage auto-discovery found `/dev/sda`.
- Auto-mount used `/mnt/embedverify-sda1`.
- The mount was automatically removed after write speed testing.

