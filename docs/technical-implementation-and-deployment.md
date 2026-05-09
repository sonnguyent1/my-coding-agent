# Technical implementation and deployment

## 1) Runtime architecture

The background process is implemented in `automation/orchestrator.py` and executed by the GitHub Actions workflow `.github/workflows/background-automation.yml`.

Workflow behavior:

1. Triggers every 10 minutes (or manually).
2. Read Trello inbox cards from `TRELLO_INBOX_LIST_ID`.
3. Build a ticket model from Trello card name/description/labels.
4. Select a target repository:
   - Optional AI hint from OpenAI (`OPENAI_API_KEY`)
   - Fallback keyword matching via `REPO_CATALOG_JSON`
5. Create an issue in the selected GitHub repository.
6. Optionally dispatch another workflow (`TARGET_AUTOMATION_WORKFLOW`) in that selected repository.
7. Move processed card to TODO (`TRELLO_TODO_LIST_ID`).
8. Scan TODO cards for related PRs, then send email notification when PR exists.
9. Optionally move notified card to DONE (`TRELLO_DONE_LIST_ID`).

## 2) Configuration model

### Required GitHub secrets

- `TRELLO_API_KEY`
- `TRELLO_TOKEN`
- `TRELLO_INBOX_LIST_ID`
- `TRELLO_TODO_LIST_ID`
- `REPO_CATALOG_JSON`
- `AUTOMATION_GITHUB_TOKEN`

### Optional secrets

- `TRELLO_DONE_LIST_ID`
- `OPENAI_API_KEY`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_SENDER`
- `EMAIL_RECIPIENT`

### Optional GitHub variables

- `OPENAI_MODEL` (default `gpt-4o-mini`)
- `TARGET_AUTOMATION_WORKFLOW`
- `TARGET_AUTOMATION_REF` (default `main`)

## 3) Deployment steps

1. Add all required secrets/variables in repository settings.
2. Ensure `AUTOMATION_GITHUB_TOKEN` has permissions for:
   - creating issues in target repositories
   - dispatching workflows (if used)
3. Enable GitHub Actions for the repository.
4. Run the `Background Ticket Automation` workflow manually once to validate setup.
5. Confirm:
   - cards move from inbox to TODO
   - issues are created in expected repositories
   - PR notification emails are sent when PRs are found

## 4) Operational notes

- No `requirements.txt` is needed; the automation uses only Python standard library modules.
- If external libraries are introduced later, add `requirements.txt` and install dependencies in workflow steps before running the orchestrator.
