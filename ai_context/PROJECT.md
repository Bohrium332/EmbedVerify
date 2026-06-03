# Project

EmbedVerify is a platform-neutral embedded hardware interface verification
framework. It standardizes three actions:

```text
execute operation -> collect result -> evaluate against rules
```

The current repository is an MVP focused on USB Host + USB storage verification.
It has already been verified on reComputer J401 / Jetson.

## Current MVP Scope

- YAML-driven board, case, and suite configuration
- CLI execution
- USB device enumeration
- USB storage discovery
- USB storage read speed
- USB storage write speed
- JSON and text reports
- Jetson J401 board profile
- Generic Linux USB/storage capabilities

## Out Of Scope For MVP

- Web UI
- MCP server
- AI analysis
- cluster scheduling
- PDF reports
- full production dashboard

## Near-Term Goal

Refine the MVP architecture so it can scale to RK, more Jetson boards, EEPROM,
ETH, NVMe, I2C, GPIO, RTC, and other modules.

