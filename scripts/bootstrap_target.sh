#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  python3-serial \
  usbutils \
  util-linux \
  coreutils \
  hdparm \
  iproute2 \
  iputils-ping \
  i2c-tools \
  gpiod \
  wireless-tools \
  iw \
  bluetooth \
  bluez \
  x11-xserver-utils \
  gstreamer1.0-tools

cd "${ROOT_DIR}"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

echo "Bootstrap complete. Activate with: source ${ROOT_DIR}/.venv/bin/activate"
