#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOARD="${BOARD:-recomputer_j401}"
STORAGE_DEVICE="${STORAGE_DEVICE:-/dev/sda}"
MOUNT_POINT="${MOUNT_POINT:-/media/seeed/USB_TEST}"
FILE_SIZE_MB="${FILE_SIZE_MB:-256}"

cd "${ROOT_DIR}"
if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
fi

ev run suites/usb_smoke.yaml \
  --board "${BOARD}" \
  --storage-device "${STORAGE_DEVICE}" \
  --mount-point "${MOUNT_POINT}" \
  --file-size-mb "${FILE_SIZE_MB}"

