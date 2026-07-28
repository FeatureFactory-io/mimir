behave.ini and dual environment.py lifecycle files.

**Existing artifact:** This ALTER targets Artifact #51 "Behave Configuration" (Code, required), currently produced by Activity #188 (Bootstrap Test Harness / TFK-02). Consumer activities already depend on it — this change updates the description to match the docs/features AT + tests/e2e layout (replacing obsolete `tests/acceptance/` / `features/at/` wording and clarifying dual environments).

**AT (docs/features/):** `behave.ini` with `paths = docs/features`, `tags = ~@wip`. `docs/features/environment.py` wires Django test client / atomic scenario isolation (`manage.py behave --simple`).

**E2E (tests/e2e/):** Invoked separately (`make test-e2e` → `manage.py behave tests/e2e/`). `tests/e2e/environment.py` wires Playwright + LiveServer, screenshots per step, optional `--base-url` / `--db-uri`.

Do not nest E2E under AT. Do not use `tests/acceptance/` or `features/at/`. Prefer `@wip` for unimplemented AT scenarios (not `@e2e` exclusion for the AT path). Produced by TFK-02 (#188). Aligns with Workflow #54 Test Automation Framework and DTA-06 / SAO.md Test Strategy.
