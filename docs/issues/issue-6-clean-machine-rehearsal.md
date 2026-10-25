[DEMO-BLOCKER] Clean-Machine Rehearsal Verification

- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  Execute a clean-machine clone and runbook verification to confirm zero undocumented local dependencies or "works on my machine" issues.
- **Acceptance Criteria:**
  - [ ] Fresh git clone in a clean environment.
  - [ ] `pip install -r backend/requirements.lock` installs cleanly.
  - [ ] `alembic upgrade head` runs cleanly on empty PostgreSQL instance.
  - [ ] `npm ci` and `npm run build` in `web/` complete with 0 errors.
  - [ ] `pytest -m "not live" backend/tests` passes 100%.
  - [ ] Vertical slice verification (Search → Chart → Paper Order → Portfolio) succeeds.
  - [ ] Console execution log saved to `docs/clean_machine_rehearsal.log` and committed.
