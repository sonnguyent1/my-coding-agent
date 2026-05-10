from __future__ import annotations

from typing import Any
from urllib import parse

from automation.http_client import _http_json


def create_issue(owner: str, repo: str, title: str, body: str, token: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    return _http_json(url, method="POST", headers=headers, payload={"title": title, "body": body})


def dispatch_workflow(owner: str, repo: str, workflow_file: str, ref: str, inputs: dict[str, str], token: str) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    _http_json(url, method="POST", headers=headers, payload={"ref": ref, "inputs": inputs})


def find_related_pr(owner: str, repo: str, ticket_id: str, token: str) -> str | None:
    query = parse.quote(f'repo:{owner}/{repo} is:pr "{ticket_id}" in:title')
    url = f"https://api.github.com/search/issues?q={query}&per_page=1"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    payload = _http_json(url, headers=headers) or {}
    items = payload.get("items", [])
    return items[0]["html_url"] if items else None
