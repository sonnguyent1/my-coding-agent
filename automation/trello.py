from __future__ import annotations

import logging
from typing import Any
from urllib import parse
from os import getenv

from automation.http_client import _http_json, _http_bytes
from automation.models import TrelloCard, TrelloAttachment, TrelloCheckItem, TrelloComment


__all__ = ["api_client"]

logger = logging.getLogger(__name__)


class _TrelloRestClient:
    """Thin Trello REST API client for authenticated requests."""

    def __init__(self, base_url: str = "https://api.trello.com/1") -> None:
        self.key = getenv("TRELLO_API_KEY")
        self.token = getenv("TRELLO_TOKEN")
        self.todo_list_id = getenv("TRELLO_TODO_LIST_ID")
        self.base_url = base_url.rstrip("/")

    def _build_url(self, path: str, **params: str) -> str:
        normalized_path = path.lstrip("/")
        query = parse.urlencode({**params})

        return f"{self.base_url}/{normalized_path}?{query}"

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = self._build_url(path, **(params or {}))
        return _http_json(url, method=method, payload=payload, 
            headers={"Authorization": f"OAuth oauth_consumer_key=\"{self.key}\", oauth_token=\"{self.token}\""})

    def fetch_cards(self, list_id: str, fields: str = "id,name,desc") -> list[TrelloCard]:
        payload = self.request(
            f"lists/{list_id}/cards",
            params={"fields": fields},
        )
        if not payload:
            return []
        return [TrelloCard.from_dict(item) for item in payload]

    def move_card_to_list(self, card_id: str, target_list_id: str) -> None:
        self.request(
            f"cards/{card_id}",
            method="PUT",
            payload={"idList": target_list_id},
        )

    def get_notifications(self, unread: bool = False) -> list[dict[str, Any]]:
        payload = self.request(
            "members/me/notifications",
            params={"read_filter": "unread" if unread else "all"},
        )
        return payload or []

    def pick_one_card_from_todo(self) -> TrelloCard | None:
        cards = self.fetch_cards(self.todo_list_id, fields="id")
        picked_card = self.get_card(cards[0].id) if cards else None
        return picked_card
    
    def get_card(self, card_id: str) -> TrelloCard:
        payload = self.request(f"cards/{card_id}")
        return TrelloCard.from_dict(payload) if payload else None

    def get_card_attachments(self, card_id: str) -> list[TrelloAttachment]:
        payload = self.request(f"cards/{card_id}/attachments") or []
        reviewed_payload = self.review_attachment_urls(card_id, payload)
        return TrelloAttachment.list_from_dict(reviewed_payload)

    def _build_attachment_download_url(self, card_id: str, attachment_id: str, file_name: str) -> str:
        encoded_name = parse.quote(file_name, safe="")
        return f"{self.base_url}/cards/{card_id}/attachments/{attachment_id}/download/{encoded_name}"

    def _is_attachment_url_valid(
        self,
        card_id: str,
        attachment_id: str,
        file_name: str,
        url: str,
    ) -> bool:
        expected_prefix = self._build_attachment_download_url(card_id, attachment_id, file_name)
        return url.startswith(expected_prefix)

    def review_attachment_urls(self, card_id: str, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure attachment URLs follow Trello download pattern and normalize when needed.

        Expected pattern:
        https://api.trello.com/1/cards/{idCard}/attachments/{idAttachment}/download/{attachmentFileName}
        """
        reviewed_payload: list[dict[str, Any]] = []
        normalized_count = 0

        for attachment in payload:
            item = dict(attachment)
            attachment_id = str(item.get("id") or "").strip()
            file_name = str(item.get("fileName") or item.get("name") or "").strip()
            current_url = str(item.get("url") or "").strip()

            if attachment_id and file_name:
                if not current_url or not self._is_attachment_url_valid(
                    card_id,
                    attachment_id,
                    file_name,
                    current_url,
                ):
                    item["url"] = self._build_attachment_download_url(card_id, attachment_id, file_name)
                    normalized_count += 1

            reviewed_payload.append(item)

        if normalized_count:
            logger.info("Normalized %s attachment URL(s) for card %s", normalized_count, card_id)

        return reviewed_payload
   
    def get_card_checklist_checkitems(self, card_id: str) -> list[TrelloCheckItem]:
        payload = self.request(f"cards/{card_id}/checklists") or []
        if not payload:
            return []
        checkitems = []
        for checklist in payload:
            checkitems.extend(TrelloCheckItem.list_from_dict(checklist.get("checkItems", [])))
        return checkitems

    def get_card_comments(self, card_id: str) -> list[TrelloComment]:
        payload = self.request(f"cards/{card_id}/actions", params={"filter": "commentCard"}) or []
        return TrelloComment.list_from_dict(payload)

    def download_attachment(self, url: str, max_bytes: int = 512 * 1024) -> bytes:
        """Download a Trello attachment file, authenticating with the stored credentials."""
        headers = {"Authorization": f"OAuth oauth_consumer_key=\"{self.key}\", oauth_token=\"{self.token}\""}
        return _http_bytes(url, headers=headers, max_bytes=max_bytes)

api_client = _TrelloRestClient()