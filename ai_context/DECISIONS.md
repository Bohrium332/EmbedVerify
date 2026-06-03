# Decisions

## 0001 - Keep Report Status But Remove Function Status

Function return values must not contain `status`. `code` is enough to represent
technical execution result.

Reports may still contain top-level `status` because it improves readability and
summary checks.

## 0002 - Board Selection Belongs To CLI Or Root Config

Suite/Fixture must not own board selection.

Selection priority:

```text
CLI --board > root config.yaml > error
```

Temporary support for `suite.board` is allowed only as backward compatibility.

## 0003 - Use Entrypoint + Lib Function Layout

Refactored modules should use:

```text
functions/<module>/<operation>.py
functions/<module>/<module>_lib.py
```

The operation entrypoint assembles framework return data. The lib owns raw
commands, parsing, and helper logic.

## 0004 - J401 Is Jetson/Tegra

The current reComputer J401 target is a Jetson/Tegra board. Do not change its
adapter to RK. Add separate RK board profiles for RK devices.

