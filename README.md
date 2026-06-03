# EmbedVerify

Platform-neutral hardware interface verification MVP.

The first milestone validates a USB Host + USB storage path on reComputer J401,
while keeping the framework open for RK, other Jetson boards, TI boards, and MCU
targets.

## Architecture

```text
Suite      test scenario, such as usb_smoke
Case       module workflow, such as usb_host_storage
Function   stable test semantic and stable output format
Capability board/platform-specific command and sysfs implementation
Board      resource and capability declaration
```

Function output stays compatible with the existing EmbedVerify contract:

```json
{
  "code": 0,
  "message": "...",
  "details": {},
  "metrics": {}
}
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

ev run suites/usb_smoke.yaml \
  --board recomputer_j401
```

The default board can also be selected from root `config.yaml`, so the normal
command can be:

```bash
ev run suites/usb_smoke.yaml
```

The runner auto-detects the first USB storage device. If the selected partition
is not mounted and the command is running as root, the write-speed test mounts it
temporarily under `/mnt/embedverify-*`, writes `.ev_write_test.bin`, removes the
file, and unmounts it after the test.

Manual overrides are still available:

```bash
ev run suites/usb_smoke.yaml \
  --board recomputer_j401 \
  --storage-device /dev/sda \
  --mount-point /media/seeed/USB_TEST
```

## Target Dependencies

Install or verify these tools on the board:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip usbutils util-linux coreutils hdparm
```

Or use the helper script from the repository root:

```bash
scripts/bootstrap_target.sh
```

Run the USB smoke suite with auto-discovery:

```bash
scripts/run_usb_smoke.sh
```

Override the detected device and mount point when needed:

```bash
STORAGE_DEVICE=/dev/sdb MOUNT_POINT=/media/seeed/MY_USB scripts/run_usb_smoke.sh
```

## Add Another Board

Add a file under `boards/`, for example:

```yaml
name: rk3576
platform: linux
adapter: rk
capabilities:
  usb: linux_generic
  storage: linux_generic
  system_info: rk
tools_required:
  - lsusb
  - lsblk
  - findmnt
  - dd
```

Generic Linux USB and storage functions can be reused across Jetson and RK
boards. Only platform-specific capabilities such as system info, thermals, GPU,
NPU, or vendor-specific sysfs paths need a board/platform adapter.
