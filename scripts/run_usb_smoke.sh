#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOARD="${BOARD:-recomputer_j401}"
STORAGE_DEVICE="${STORAGE_DEVICE:-}"
MOUNT_POINT="${MOUNT_POINT:-}"
FILE_SIZE_MB="${FILE_SIZE_MB:-256}"

cd "${ROOT_DIR}"
if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
fi

ARGS=(
  run
  suites/usb_smoke.yaml
  --board "${BOARD}"
  --file-size-mb "${FILE_SIZE_MB}"
)

if [[ -n "${STORAGE_DEVICE}" ]]; then
  ARGS+=(--storage-device "${STORAGE_DEVICE}")
fi

if [[ -n "${MOUNT_POINT}" ]]; then
  ARGS+=(--mount-point "${MOUNT_POINT}")
fi

ev "${ARGS[@]}"
