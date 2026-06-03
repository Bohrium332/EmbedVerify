# Conventions

## Board Selection

Board selection must not be owned by Suite/Fixture.

Required priority:

```text
CLI --board > root config.yaml > error
```

`suite.board` may be temporarily supported for backward compatibility, but new
suite configs should not use it.

## Function Return

Function return must not contain `status`.

Required shape:

```json
{
  "code": 0,
  "message": "...",
  "details": {},
  "metrics": {}
}
```

`code` expresses technical execution result. `metrics` contains collected
measurement data. Case `expect.rules` decides pass/fail.

Top-level reports may still contain `status` for readability:

```json
{
  "status": "passed"
}
```

## Code Values

Use these values unless a module has a documented extension:

| Code | Meaning |
| --- | --- |
| `0` | execution succeeded |
| `1` | timeout |
| `-1` | execution failed |
| `-2` | environment/tool missing |
| `-101` | device not found |
| `-102` | device abnormal |
| `-103` | path/file not found |

## Function Layout

Use entrypoint + lib layout for new/refactored modules:

```text
functions/<module>/<operation>.py
functions/<module>/<module>_lib.py
```

The lib returns raw data or plain helper structures. The operation entrypoint
returns the framework contract.

## Reporting To User

After every execution turn, include:

```text
本轮完成：
下一轮待办：
下下轮待办：
```

