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

## Latest Passing Metrics

```text
board: recomputer_j401
USB device: Kingston DataTraveler 3.0
USB speed: 5G
read_speed_mbps: 159.0
write_speed_mbps: 17.2
```

## Next Round

- Add root `config.yaml`.
- Implement board selection priority: CLI `--board` > `config.yaml` > error.
- Remove board binding from `suites/usb_smoke.yaml`.
- Remove `status` from Function return values.
- Update Case expectations to use `code + metrics`.
- Split `usb.py` and `storage.py` into entrypoint + `*_lib.py` layout.

## Round After Next

- Add `skip_on_fail`.
- Add `label` / `save_output`.
- Add `{{...}}` template references.
- Change reports to timestamped report directories.

