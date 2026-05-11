from __future__ import annotations

import json
from os import getenv

from dotenv import load_dotenv

from automation.email import send_email_notification
from automation.github import find_related_pr
from automation.http_client import _require_env
from automation.models import RepoCandidate, Ticket
from automation.trello import fetch_trello_cards, move_card_to_list

load_dotenv()


def parse_repo_catalog(raw_catalog: str) -> list[RepoCandidate]:
    payload = json.loads(raw_catalog)
    return [
        RepoCandidate(full_name=item["full_name"], keywords=item.get("keywords", []))
        for item in payload
    ]


def select_repository(ticket: Ticket, candidates: list[RepoCandidate], ai_hint: str | None = None) -> RepoCandidate:
    if not candidates:
        raise ValueError("No repository candidates configured")

    normalized_hint = (ai_hint or "").strip().lower()
    for candidate in candidates:
        if normalized_hint and normalized_hint == candidate.full_name.lower():
            return candidate

    haystack = f"{ticket.title} {ticket.description} {' '.join(ticket.labels)}".lower()
    scored = sorted(
        candidates,
        key=lambda candidate: sum(1 for keyword in candidate.keywords if keyword.lower() in haystack),
        reverse=True,
    )
    return scored[0]


def build_issue_body(ticket: Ticket) -> str:
    label_line = ", ".join(ticket.labels) if ticket.labels else "none"
    return (
        "Automated ticket intake from Trello.\n\n"
        f"- Ticket ID: {ticket.id}\n"
        f"- Title: {ticket.title}\n"
        f"- Labels: {label_line}\n\n"
        "### Requirement\n"
        f"{ticket.description.strip() or '(no description provided)'}\n\n"
        "### Requested Action\n"
        "Implement the requirement, commit with a descriptive message, and open a pull request."
    )


def run() -> int:
    trello_key = _require_env("TRELLO_API_KEY")
    trello_token = _require_env("TRELLO_TOKEN")
    todo_list_id = _require_env("TRELLO_TODO_LIST_ID")
    doing_list_id = _require_env("TRELLO_DOING_LIST_ID")
    done_list_id = getenv("TRELLO_DONE_LIST_ID")
    github_token = _require_env("GITHUB_TOKEN")
    repo_catalog = parse_repo_catalog(_require_env("REPO_CATALOG_JSON"))

    todo_cards = fetch_trello_cards(todo_list_id, key=trello_key, token=trello_token)

    # Move one card from TODO to DOING
    doing_card_id: str | None = None
    if todo_cards:
        doing_card_id = todo_cards[0]["id"]
        move_card_to_list(doing_card_id, doing_list_id, key=trello_key, token=trello_token)

    # Check remaining TODO cards for related PRs and move to DONE
    for raw in todo_cards:
        if raw["id"] == doing_card_id:
            continue
        ticket = Ticket(
            id=raw["shortLink"],
            title=raw["name"],
            description=raw.get("desc", ""),
            labels=[label.get("name", "").strip() for label in raw.get("labels", []) if label.get("name")],
        )
        target_repo = select_repository(ticket, repo_catalog, ai_hint=None)
        if "/" not in target_repo.full_name:
            raise ValueError(f"Repository full_name must be in owner/repo format: {target_repo.full_name}")
        owner, repo = target_repo.full_name.split("/", 1)
        pr_url = find_related_pr(owner, repo, ticket.id, github_token)
        if pr_url:
            send_email_notification(pr_url, ticket)
            if done_list_id:
                move_card_to_list(raw["id"], done_list_id, key=trello_key, token=trello_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
