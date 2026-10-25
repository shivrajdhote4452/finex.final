[DEMO-BLOCKER] Enable Branch Protection on main

- **Labels:** `demo-blocker`
- **Assignee:** `@shivrajdhote4452`
- **Description:**
  CI has quality gates and test suites, but direct git pushes to `main` are currently possible. Protect `main` against accidental untested pushes or forced pushes.
- **Acceptance Criteria:**
  - [ ] GitHub Repo Settings → Branches → Add branch protection rule for `main`.
  - [ ] "Require a pull request before merging" is enabled.
  - [ ] "Require status checks to pass before merging" is enabled (`backend-quality-gates`, `web-quality-gates`).
  - [ ] "Do not allow bypassing the above settings" is enabled.
  - [ ] Direct `git push origin main` from a local commit is rejected by GitHub remote.
