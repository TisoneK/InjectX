# Golden vectors

The parity fixtures for the Kotlin port (ADR-10). `generate_goldens.py` runs
the **reference Python backend** (`backend/parser/parse_engine.parse_config`)
over every sample in `assets/configs/` and writes one deterministic fixture per
file to `fixtures/`. The `:core` Kotlin tests load these and assert the port
produces identical normalized output.

Regenerate (from the repo root) after changing the backend or adding samples:

```bash
backend/.venv/bin/python android/goldens/generate_goldens.py
```

- Fixtures are deterministic: timestamps and `elapsed_ms` are scrubbed and
  `filepath` is rewritten repo-relative, so re-runs diff cleanly in git.
- `index.json` lists every fixture with its format / scheme / decryption status.
- Coverage mirrors which formats have committed samples — see `../TASKS.md`.
  Schemes without samples (hat, npv, nsh, vhd, legacy hc/ehi) have no fixtures
  yet (backlog N3).
