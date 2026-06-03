# Codex Project Instructions

This repository is the MVP branch of EmbedVerify, a platform-neutral embedded
hardware interface verification framework.

Before editing, read:

1. `ai_context/README.md`
2. `ai_context/CONVENTIONS.md`
3. `ai_context/PROGRESS.md`
4. `ai_context/HANDOFF.md`

After every execution turn, report in this format:

```text
本轮完成：
下一轮待办：
下下轮待办：
```

Critical rules:

- Do not put board selection in suite/fixture configs.
- Board selection priority must be: CLI `--board` > root `config.yaml` > error.
- Function return must not contain `status`.
- Top-level reports may contain `status` for readability.
- Keep `recomputer_j401` as a Jetson/Tegra board profile, not RK.
- Preserve the platform-neutral capability mapping model.

