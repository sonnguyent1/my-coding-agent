from __future__ import annotations

import json
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any
from urllib import error, parse, request


@dataclass(frozen=True)
class Ticket:
    id: str
    title: str
    description: str
    labels: list[str]


@dataclass(frozen=True)
class RepoCandidate:
    full_name: str
    keywords: list[str]


def _http_json(url: str, method: str = "GET", headers: dict[str, str] | None = None, payload: dict[str, Any] | None = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, headers=headers or {}, data=body)
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return None if not raw else json.loads(raw)
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {details}") from exc


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


def _trello_url(path: str, *, key: str, token: str, **params: str) -> str:
    query = parse.urlencode({"key": key, "token": token, **params})
    return f"https://api.trello.com/1/{path}?{query}"


def fetch_trello_cards(list_id: str, *, key: str, token: str) -> list[dict[str, Any]]:
    url = _trello_url(f"lists/{list_id}/cards", key=key, token=token, fields="name,desc,labels,shortLink")
    return _http_json(url) or []


def move_card_to_list(card_id: str, target_list_id: str, *, key: str, token: str) -> None:
    url = _trello_url(f"cards/{card_id}", key=key, token=token)
    _http_json(url, method="PUT", payload={"idList": target_list_id})


def create_issue(owner: str, repo: str, title: str, body: str, token: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    return _http_json(url, method="POST", headers=headers, payload={"title": title, "body": body})


def dispatch_workflow(owner: str, repo: str, workflow_file: str, ref: str, inputs: dict[str, str], token: str) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    _http_json(url, method="POST", headers=headers, payload={"ref": ref, "inputs": inputs})


def find_related_pr(owner: str, repo: str, ticket_id: str, token: str) -> str | None:
    query = parse.quote(f'repo:{owner}/{repo} is:pr "{ticket_id}" in:title')
    url = f"https://api.github.com/search/issues?q={query}&per_page=1"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    payload = _http_json(url, headers=headers) or {}
    items = payload.get("items", [])
    return items[0]["html_url"] if items else None


def request_ai_repo_hint(ticket: Ticket, candidates: list[RepoCandidate], api_key: str | None) -> str | None:
    if not api_key:
        return None

    prompt = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "user",
                "content": (
                    "Choose the most relevant repository full name from the list only.\n"
                    f"Repositories: {', '.join(candidate.full_name for candidate in candidates)}\n"
                    f"Ticket title: {ticket.title}\n"
                    f"Ticket description: {ticket.description}\n"
                    f"Ticket labels: {', '.join(ticket.labels)}\n"
                    "Output only the repository full name."
                ),
            }
        ],
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = _http_json("https://api.openai.com/v1/chat/completions", method="POST", headers=headers, payload=prompt)
    choices = payload.get("choices", []) if payload else []
    if choices:
        message = choices[0].get("message", {})
        text = message.get("content")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def send_email_notification(pr_url: str, ticket: Ticket) -> None:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("EMAIL_SENDER")
    recipient = os.environ.get("EMAIL_RECIPIENT")
    if not all([host, username, password, sender, recipient]):
        return

    msg = EmailMessage()
    msg["Subject"] = f"PR ready for review: {ticket.title}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(f"Ticket {ticket.id} now has a pull request ready:\n{pr_url}")

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(msg)


def run() -> int:
    trello_key = os.environ["TRELLO_API_KEY"]
    trello_token = os.environ["TRELLO_TOKEN"]
    inbox_list_id = os.environ["TRELLO_INBOX_LIST_ID"]
    todo_list_id = os.environ["TRELLO_TODO_LIST_ID"]
    github_token = os.environ["GITHUB_TOKEN"]
    repo_catalog = parse_repo_catalog(os.environ["REPO_CATALOG_JSON"])
    workflow_file = os.environ.get("TARGET_AUTOMATION_WORKFLOW", "").strip()
    workflow_ref = os.environ.get("TARGET_AUTOMATION_REF", "main")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    cards = fetch_trello_cards(inbox_list_id, key=trello_key, token=trello_token)
    for raw in cards:
        ticket = Ticket(
            id=raw["shortLink"],
            title=raw["name"],
            description=raw.get("desc", ""),
            labels=[label.get("name", "").strip() for label in raw.get("labels", []) if label.get("name")],
        )
        ai_hint = request_ai_repo_hint(ticket, repo_catalog, openai_api_key)
        target_repo = select_repository(ticket, repo_catalog, ai_hint=ai_hint)
        if "/" not in target_repo.full_name:
            raise ValueError(f"Repository full_name must be in owner/repo format: {target_repo.full_name}")
        owner, repo = target_repo.full_name.split("/", 1)
        issue = create_issue(
            owner=owner,
            repo=repo,
            title=f"[Automation] {ticket.id} - {ticket.title}",
            body=build_issue_body(ticket),
            token=github_token,
        )
        if workflow_file:
            dispatch_workflow(
                owner=owner,
                repo=repo,
                workflow_file=workflow_file,
                ref=workflow_ref,
                inputs={"issue_number": str(issue["number"]), "ticket_id": ticket.id},
                token=github_token,
            )
        move_card_to_list(raw["id"], todo_list_id, key=trello_key, token=trello_token)
        pr_url = find_related_pr(owner, repo, ticket.id, github_token)
        if pr_url:
            send_email_notification(pr_url, ticket)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
