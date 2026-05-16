# my-coding-agent

Background automation project that:

1. Polls Trello for newly created tickets in an inbox list and moves them to TODO.
2. Reads ticket details (name, description, tags).
3. Uses an AI hint (optional) plus keyword routing to select the most relevant GitHub repository.
4. Creates an implementation issue in that repository and optionally dispatches a coding workflow that can commit and create a PR.
5. Checks TODO tickets for related PRs and emails you once one is found, so you can review/approve or apply manual fixes. If `TRELLO_DONE_LIST_ID` is configured, notified cards are moved to DONE to avoid duplicate notifications.

## Package Layout

- `automation` - Installable Python package for the automation workflow.
- `automation/orchestrator.py` - Package entry point and orchestrator runner.
- `automation/__main__.py` - Enables `python -m automation`.
- `tests/test_package.py` - Basic package smoke test.
- `pyproject.toml` - Build metadata and console script definition.

## Dependencies

Install the package in editable mode for local development:

```bash
pip install -e .
```

The project uses `python-dotenv` to load environment variables from a `.env` file for local runs.

You can also run the package directly:

```bash
python -m automation
automation-orchestrator
```

## Configuration

Set these repository secrets:

- `TRELLO_API_KEY`
- `TRELLO_TOKEN`
- `TRELLO_INBOX_LIST_ID`
- `TRELLO_TODO_LIST_ID`
- `TRELLO_DONE_LIST_ID` (optional but recommended for one-time PR notifications)
- `REPO_CATALOG_JSON` (JSON list, for example:
  `[{"full_name":"your-org/repo-a","keywords":["api","backend"]},{"full_name":"your-org/repo-b","keywords":["ui","frontend"]}]`)
- `AUTOMATION_GITHUB_TOKEN` (token with repo + workflow permissions on target repos)
- `OPENAI_API_KEY` (optional, for AI repo hinting)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_SENDER`, `EMAIL_RECIPIENT` (optional, email notification)

Optional repository variables:

- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `TARGET_AUTOMATION_WORKFLOW` (workflow file name in selected repo to trigger implementation)
- `TARGET_AUTOMATION_REF` (default branch/ref for dispatch, default: `main`)

## Local test

```bash
python -m unittest discover -s tests -p "test_*.py"
```
