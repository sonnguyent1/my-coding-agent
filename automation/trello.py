from __future__ import annotations

from typing import Any
from urllib import parse

from automation.http_client import _http_json


def _trello_url(path: str, *, key: str, token: str, **params: str) -> str:
    query = parse.urlencode({"key": key, "token": token, **params})
    return f"https://api.trello.com/1/{path}?{query}"


def fetch_trello_cards(list_id: str, *, key: str, token: str) -> list[dict[str, Any]]:
    url = _trello_url(f"lists/{list_id}/cards", key=key, token=token, fields="name,desc,labels,shortLink")
    return _http_json(url) or []


def move_card_to_list(card_id: str, target_list_id: str, *, key: str, token: str) -> None:
    url = _trello_url(f"cards/{card_id}", key=key, token=token)
    _http_json(url, method="PUT", payload={"idList": target_list_id})
