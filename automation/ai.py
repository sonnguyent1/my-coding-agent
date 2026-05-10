from __future__ import annotations

from os import getenv

from automation.http_client import _http_json
from automation.models import RepoCandidate, Ticket


def request_ai_repo_hint(ticket: Ticket, candidates: list[RepoCandidate], api_key: str | None) -> str | None:
    if not api_key:
        return None

    prompt = {
        "model": getenv("OPENAI_MODEL", "gpt-4o-mini"),
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
