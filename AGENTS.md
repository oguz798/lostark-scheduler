# Project Learning Workflow

Default behavior for this repository:
1. Start each new session by showing the full refactor/readability checklist once.
2. Keep checklist output concise with headings and numbered items.
3. During the same session, do not repeat the full checklist unless explicitly requested.
4. Use a short "checklist active" reminder on later turns when relevant.
5. For implementation requests, first acknowledge transition from learning-only mode for that task.

## Refactor/Readability Checklist
1. Confirm architecture boundaries (`ui/pages`, `app/services`, `app/db.py`, `app/schemas.py`).
2. Standardize naming (`create_*`, `update_*`, `delete_*`, `get_*`, `prepare_*`).
3. Remove dead/duplicate code and legacy leftovers.
4. Keep service workflows cohesive and validate early.
5. Standardize error handling and user-facing messages.
6. Standardize UI patterns (forms, list/detail, dialogs, notifications).
7. Add sparse, high-value comments that explain "why".
8. Add service-level tests (happy paths + validation failures).
9. Document current workflow behavior in README sections.
10. Run sanity checks (lint/format/tests/manual smoke) before feature work.
