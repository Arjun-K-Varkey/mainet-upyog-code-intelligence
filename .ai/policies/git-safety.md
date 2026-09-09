# Git Safety Policy

- Never work directly on `main` for feature implementation.
- Use a dedicated branch.
- Inspect `git status` and `git diff` before committing.
- Keep commits focused and explainable.
- Do not rewrite history unless explicitly authorized.
- Do not commit secrets, credentials, generated private data, or source-system dumps.
- Prefer pull requests and human acceptance for consequential changes.
