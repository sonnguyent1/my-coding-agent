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
    import asyncio

    from copilot import CopilotClient
    from copilot.generated.session_events import AssistantMessageData, SessionIdleData
    from copilot.session import PermissionHandler

    async def main():
        client = CopilotClient()
        await client.start()

        # Create a session (on_permission_request is required)
        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model="gpt-4o",
        )

        done = asyncio.Event()

        def on_event(event):
            match event.data:
                case AssistantMessageData() as data:
                    print(data.content)
                case SessionIdleData():
                    done.set()

        session.on(on_event)
        await session.send("What is 2+2?")
        await done.wait()

        # Clean up manually
        await session.disconnect()
        await client.stop()

    asyncio.run(main())
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
