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
| `2` | skipped by runner |
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

## Case Flow Controls

Function entries may use these runner-level fields:

```yaml
label: storage_info
skip_on_fail: true
save_output: true
```

`label` gives a stable reference name for reports and templates.

`skip_on_fail: true` means this function is skipped when an earlier function in
the same Case failed expectation. The runner emits `code: 2` for the skipped
record and marks its expectation policy as `skipped`; the original failed
record still controls the Case/Suite failure.

`save_output: true` writes that function's execution record to
`reports/<timestamp>_<request_id>_<status>/outputs/`.

Parameter templates use `{{ ... }}` and should reference labels from earlier
functions in the same Case:

```yaml
device: "{{ storage_info.result.details.discovery.disk }}"
```

When the whole value is a template, the resolved value keeps its original type.
When a template is embedded inside a larger string, the resolved value is
stringified.

## Report Layout

Reports are written under a timestamped request directory:

```text
reports/YYYYMMDDTHHMMSSZ_<request_id>_<status>/
├── report.json
├── report.txt
└── outputs/
```

## Storage Write Safety

Storage write tests may auto-mount an unmounted USB partition only after a
read-only health check when the partition is ext2/ext3/ext4.

If `tune2fs -l` reports a filesystem state other than `clean`, the write test
must fail before mounting or writing. The report should include the parsed
filesystem health and recent storage-related dmesg errors when available.

Keep `needs_recovery` in the health details as a diagnostic flag. Do not block
only on that flag when `Filesystem state` is explicitly `clean`; some clean or
recently mounted ext filesystems can expose the flag while still being safe for
the intended write smoke.

## Reporting To User

After every execution turn, include:

```text
本轮完成：
下一轮待办：
下下轮待办：
```
