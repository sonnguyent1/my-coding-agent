from __future__ import annotations

import asyncio
import logging
import os
from os import getenv
from typing import Any

from automation.agents import CopilotTaskPlan
from copilot import CopilotClient, SubprocessConfig
from copilot.generated.session_events import AssistantMessageData
from copilot.session import Attachment, PermissionHandler


logger = logging.getLogger(__name__)

def _build_attachments(paths: list[str]) -> list[Attachment]:
    """Convert local file paths to FileAttachment dicts, skipping missing files."""
    attachments: list[Attachment] = []
    for path in paths:
        if os.path.isfile(path):
            attachments.append({"type": "file", "path": path, "displayName": os.path.basename(path)})
        else:
            logger.warning("Attachment file not found, skipping: %s", path)
    return attachments


def _build_dispatch_prompt(plan: CopilotTaskPlan, repository_hint: str | None) -> str:
    payload = plan.as_copilot_sdk_payload()
    acceptance_criteria = payload.get("acceptanceCriteria", [])
    suggested_files = payload.get("suggestedFiles", [])
    risk_notes = payload.get("riskNotes", [])

    criteria_text = "\n".join(f"- {item}" for item in acceptance_criteria) or "- Follow best practices"
    files_text = "\n".join(f"- {item}" for item in suggested_files) or "- infer from context"
    risks_text = "\n".join(f"- {item}" for item in risk_notes) or "- none"

    return (
        f"You are implementing a planned software task in a repository.\n\n"
        f"Repository hint: {repository_hint or 'not specified'}\n"
        f"Planner model: {payload.get('plannerModel', 'unknown')}\n"
        f"Task title: {payload.get('title', '')}\n\n"
        f"Primary implementation instructions:\n"
        f"{payload.get('instructions', '')}\n\n"
        f"Acceptance criteria:\n{criteria_text}\n\n"
        f"Suggested files to inspect/edit:\n{files_text}\n\n"
        f"Risk notes to consider:\n{risks_text}\n\n"
        "Execution requirements:\n"
        "- Implement the requested code changes completely.\n"
        "- Run relevant checks/tests and include results in your summary.\n"
        "- Respond only with the following JSON format:\n"
        "  {\"status\": \"OK\"|\"FAILED\", \"pullRequestUrl\": <URL of the Pull request>}\n"
        "- Commit changes using a clear, conventional commit message.\n"
        "- Create a proper pull request after implementation is complete.\n"
        "- Ensure the pull request is visible in the Pull Request section of the GitHub site.\n"
        "- PR title must be concise and descriptive of the functional change.\n"
        "- PR body must include: summary of changes, files touched, test evidence, and risks/rollback notes.\n"
        "- Link the PR description to the task context and acceptance criteria above.\n"
    )


async def _dispatch_copilot_plan_async(plan: CopilotTaskPlan) -> dict[str, Any]:
    github_token = getenv("COPILOT_GITHUB_TOKEN")
    repository_hint = getenv("COPILOT_TARGET_REPOSITORY")
    model = getenv("COPILOT_MODEL", "auto")
    working_directory = getenv("COPILOT_WORKING_DIRECTORY")

    timeout_raw = getenv("COPILOT_SEND_TIMEOUT_SECONDS", "300")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 300.0

    prompt = _build_dispatch_prompt(plan, repository_hint)
    attachments = _build_attachments(plan.attachment_paths)
    if attachments:
        logger.info("Attaching %d file(s) to Copilot session prompt", len(attachments))

    async with CopilotClient(SubprocessConfig(github_token=github_token, use_logged_in_user=False)) as client:
        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model=model,
            working_directory=working_directory,
            github_token=github_token,
        )
        logger.info("Created CopilotClient session: %s", session.session_id)
        try:
            logger.info("Sending prompt to Copilot session with timeout of %s seconds", timeout_seconds)
            logger.info("Sending prompt to Copilot session: %s", prompt)
            event = await session.send_and_wait(
                prompt,
                attachments=attachments or None,
                timeout=timeout_seconds,
            )
            logger.info("Received response from Copilot session (event_type=%s)", getattr(event, "type", None))

            assistant_text = ""
            message_id = None
            if event and isinstance(event.data, AssistantMessageData):
                assistant_text = event.data.content
                message_id = event.data.message_id
            else:
                for history_event in reversed(await session.get_messages()):
                    if isinstance(history_event.data, AssistantMessageData):
                        assistant_text = history_event.data.content
                        message_id = history_event.data.message_id
                        break

            if assistant_text:
                logger.info("Copilot response: %s", assistant_text)

            return {
                "status": "sent",
                "repository": repository_hint,
                "model": model,
                "session_id": session.session_id,
                "assistant_message_id": message_id,
                "assistant_message": assistant_text,
            }
        finally:
            await session.disconnect()


def dispatch_copilot_plan(plan: CopilotTaskPlan) -> dict[str, Any]:
    """Dispatch a plan using the documented copilot SDK session flow."""
    logger.info("Dispatching plan via copilot.CopilotClient session flow")
    try:
        result = asyncio.run(_dispatch_copilot_plan_async(plan))
    except RuntimeError as exc:
        # If called from an existing event loop, surface a clearer error.
        if "asyncio.run() cannot be called from a running event loop" in str(exc):
            raise RuntimeError(
                "dispatch_copilot_plan() cannot be called from within an active event loop. "
                "Use _dispatch_copilot_plan_async() in async contexts."
            ) from exc
        raise

    logger.info("Copilot dispatch completed for session: %s", result.get("session_id"))
    return result