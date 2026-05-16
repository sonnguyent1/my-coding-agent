from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from os import getenv
from typing import Any

try:
	from openai import OpenAI
except ImportError:
	OpenAI = None

from automation.models import TrelloAttachment, TrelloCard, TrelloCheckItem, TrelloComment

# Avoid a hard import cycle — DownloadedAttachment is referenced by string annotation only.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from automation.attachments import DownloadedAttachment


@dataclass(frozen=True)
class CopilotTaskPlan:
	"""Structured planning payload for downstream GitHub Copilot agent execution."""

	model: str
	task_title: str
	implementation_prompt: str
	acceptance_criteria: list[str]
	suggested_files: list[str]
	risk_notes: list[str]
	context_data: dict[str, Any]
	raw_response: str
	attachment_paths: list[str] = dataclasses.field(default_factory=list)

	def as_copilot_sdk_payload(self) -> dict[str, Any]:
		"""Return a generic payload shape that can be adapted for github-copilot-sdk calls."""
		return {
			"title": self.task_title,
			"instructions": self.implementation_prompt,
			"acceptanceCriteria": self.acceptance_criteria,
			"suggestedFiles": self.suggested_files,
			"riskNotes": self.risk_notes,
			"context": self.context_data,
			"plannerModel": self.model,
		}


class CopilotPlanningAgent:
	"""Use Qwen to transform Trello work items into implementation-ready Copilot tasks."""

	def __init__(
		self,
		*,
		api_key: str | None = None,
		base_url: str | None = None,
		model: str | None = None,
		temperature: float = 0.2,
	) -> None:
		self.api_key = api_key or getenv("LLM_API_KEY")
		self.base_url = (base_url or getenv("LLM_API_BASE_URL")).rstrip("/")
		self.model = model or getenv("LLM_MODEL")
		self.temperature = temperature

	def build_context(
		self,
		*,
		card: TrelloCard,
		check_items: list[TrelloCheckItem],
		attachments: list[TrelloAttachment],
		comments: list[TrelloComment],
		downloaded_files: list[DownloadedAttachment] | None = None,
		repository_hint: str | None = None,
	) -> dict[str, Any]:
		limited_comments = comments[:3]
		limited_attachments = attachments[:3]

		context: dict[str, Any] = {
			"card": {
				"name": card.name,
				"description": card.desc,
			},
			"checkItems": [
				{
					"name": item.name,
				}
				for item in check_items
			],
			"attachments": [
				{
					"name": item.name,
					"mimeType": item.mime_type,
					"url": item.url,
				}
				for item in limited_attachments
			],
			"comments": [
				{
					"text": item.data.text[:800],
				}
				for item in limited_comments
			],
		}

		if downloaded_files:
			context["attachmentContents"] = [
				{
					"name": f.name,
					"mimeType": f.mime_type,
					"localPath": f.local_path,
					"contentSnippet": f.content_snippet,
				}
				for f in downloaded_files
				if f.content_snippet
			]

		return context

	def generate_plan(
		self,
		*,
		card: TrelloCard,
		check_items: list[TrelloCheckItem],
		attachments: list[TrelloAttachment],
		comments: list[TrelloComment],
		downloaded_files: list[DownloadedAttachment] | None = None,
		repository_hint: str | None = None,
	) -> CopilotTaskPlan:
		if not self.api_key:
			raise ValueError("LLM_API_KEY is required")
		if OpenAI is None:
			raise RuntimeError("openai package is required; install it with pip install openai")

		context_data = self.build_context(
			card=card,
			check_items=check_items,
			attachments=attachments,
			comments=comments,
			downloaded_files=downloaded_files,
			repository_hint=repository_hint,
		)

		system_prompt = (
			"You are a software architect. Convert Trello work items into coding-agent tasks. "
			"Be concise. Output valid JSON only."
		)
		user_prompt = (
			"Produce JSON with exactly these keys: "
			"task_title, implementation_prompt, acceptance_criteria, suggested_files, risk_notes.\n"
			"implementation_prompt: direct, executable instructions for a coding agent.\n"
			"acceptance_criteria/suggested_files/risk_notes: arrays of short strings.\n\n"
			f"Context:\n{json.dumps(context_data, ensure_ascii=False)}"
		)

		client = OpenAI(api_key=self.api_key, base_url=self.base_url)
		stream = client.chat.completions.create(
			model=self.model,
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			temperature=self.temperature,
			max_tokens=1024,
			stream=True,
		)
		text = self._collect_stream_text(stream)
		parsed = self._extract_json_object(text)

		return CopilotTaskPlan(
			model=self.model,
			task_title=str(parsed.get("task_title", card.name)).strip() or card.name,
			implementation_prompt=str(parsed.get("implementation_prompt", "")).strip(),
			acceptance_criteria=self._as_string_list(parsed.get("acceptance_criteria")),
			suggested_files=self._as_string_list(parsed.get("suggested_files")),
			risk_notes=self._as_string_list(parsed.get("risk_notes")),
			context_data=context_data,
			raw_response=text,
			attachment_paths=[f.local_path for f in (downloaded_files or [])],
		)

	@staticmethod
	def _collect_stream_text(stream: Any) -> str:
		parts: list[str] = []
		for chunk in stream:
			if not getattr(chunk, "choices", None):
				continue
			delta = chunk.choices[0].delta
			content = getattr(delta, "content", None)
			if isinstance(content, str) and content:
				parts.append(content)
		return "".join(parts)

	@staticmethod
	def _extract_json_object(text: str) -> dict[str, Any]:
		if not text.strip():
			return {}

		direct = CopilotPlanningAgent._try_json(text)
		if direct is not None:
			return direct

		fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
		if fenced:
			parsed = CopilotPlanningAgent._try_json(fenced.group(1))
			if parsed is not None:
				return parsed

		loose = re.search(r"(\{.*\})", text, flags=re.DOTALL)
		if loose:
			parsed = CopilotPlanningAgent._try_json(loose.group(1))
			if parsed is not None:
				return parsed

		return {}

	@staticmethod
	def _try_json(text: str) -> dict[str, Any] | None:
		try:
			parsed = json.loads(text)
		except json.JSONDecodeError:
			return None
		return parsed if isinstance(parsed, dict) else None

	@staticmethod
	def _as_string_list(value: Any) -> list[str]:
		if not isinstance(value, list):
			return []
		return [str(item).strip() for item in value if str(item).strip()]
