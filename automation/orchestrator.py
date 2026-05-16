from __future__ import annotations

import logging
from typing import Any
from os import getenv

from dotenv import load_dotenv
from automation.trello import api_client
from automation.models import TrelloCard
from automation.agents import CopilotTaskPlan, CopilotPlanningAgent
from automation.attachments import download_card_attachments
from automation.copilot import dispatch_copilot_plan


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_current_unread_notifications() -> list[dict[str, Any]]:
    """Fetch unread notifications for the authenticated Trello account."""
    logger.info("Fetching current unread notifications...")
    notifications = api_client.get_notifications(unread=True)
    logger.info(f"Retrieved {len(notifications)} unread notifications")
    return notifications

def get_todo_card() -> TrelloCard | None:
    """Fetch a single card from the configured TODO list."""
    logger.info("Fetching a card from the TODO list...")
    card = api_client.pick_one_card_from_todo()
    if card:
        attachments = api_client.get_card_attachments(card.id)
        logger.info(f"Retrieved card: {card.name} with {len(attachments)} attachments")
        checkitems = api_client.get_card_checklist_checkitems(card.id)
        logger.info(f"Card has {len(checkitems)} checklist items")
        comments = api_client.get_card_comments(card.id)
        logger.info(f"Card has {len(comments)} comments")
    else:
        logger.info("No cards available in TODO list")
    return card


def run() -> int:
    """Orchestrator for running the automation."""
    logger.info("Starting automation orchestrator...")
    enable_dispatch = getenv("ENABLE_COPILOT_DISPATCH", "0") == "1"
    repository_hint = getenv("COPILOT_TARGET_REPOSITORY", None)

    if repository_hint:
        logger.info(f"Using repository hint for Copilot planning: {repository_hint}")
    elif enable_dispatch:
        logger.error("No repository hint provided for Copilot dispatch (set COPILOT_TARGET_REPOSITORY env var)")
        return 1
    else:
        logger.warning("No repository hint provided; planning will continue and dispatch remains disabled")

    plan = build_copilot_plan_for_todo_card(repository_hint=repository_hint)
    if not plan:
        logger.error("Failed to build a Copilot task plan from TODO card")
        return 1

    try:
        if plan:
            logger.info("Copilot plan ready: %s", plan.task_title)
            if enable_dispatch:
                try:
                    result = dispatch_copilot_plan(plan)
                    logger.info("Copilot dispatch result: %s", result.get("status", "unknown"))
                except Exception as sdk_exc:
                    logger.error("Failed to dispatch Copilot SDK task: %s", sdk_exc)
                    return 1
            else:
                logger.info("Skipping Copilot dispatch (set ENABLE_COPILOT_DISPATCH=1 to enable)")
    except ValueError as exc:
        logger.warning("Skipping Copilot planning: %s", exc)

    logger.info("Automation orchestrator completed successfully")
    return 0


def build_copilot_plan_for_todo_card(repository_hint: str | None = None) -> CopilotTaskPlan | None:
    """Build an implementation-ready task plan for the current TODO card using Copilot."""
    card = api_client.pick_one_card_from_todo()
    if not card:
        logger.info("No TODO card found for Copilot planning")
        return None

    attachments = api_client.get_card_attachments(card.id)
    logger.info(
        "Building Copilot plan for card: %s with the following attachments: %s",
        card.name,
        [a.url for a in attachments] if attachments else "No attachments",
    )
    checkitems = api_client.get_card_checklist_checkitems(card.id)
    comments = api_client.get_card_comments(card.id)

    downloaded_files = download_card_attachments(attachments)

    enable_planning = getenv("ENABLE_COPILOT_PLANNING", "1") == "1"
    if not enable_planning:
        logger.info("Copilot planning is disabled (set ENABLE_COPILOT_PLANNING=1 to enable)")
        return None
    agent = CopilotPlanningAgent()
    plan = agent.generate_plan(
        card=card,
        attachments=attachments,
        check_items=checkitems,
        comments=comments,
        downloaded_files=downloaded_files,
        repository_hint=repository_hint,
    )
    logger.info("Generated Copilot task plan: %s", plan.task_title)
    return plan


if __name__ == "__main__":
    raise SystemExit(run())
