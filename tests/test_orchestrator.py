import os
import unittest
from unittest.mock import MagicMock, call, patch

from automation.orchestrator import RepoCandidate, Ticket, build_issue_body, run, select_repository


class SelectRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ticket = Ticket(
            id="abc123",
            title="Add payment webhook retries",
            description="Retry failed Stripe webhook processing in backend worker.",
            labels=["backend", "payment"],
        )
        self.repos = [
            RepoCandidate(full_name="org/frontend-app", keywords=["frontend", "react"]),
            RepoCandidate(full_name="org/backend-api", keywords=["backend", "payment", "worker"]),
        ]

    def test_select_repository_uses_ai_hint_when_exact_match(self) -> None:
        selected = select_repository(self.ticket, self.repos, ai_hint="org/backend-api")
        self.assertEqual("org/backend-api", selected.full_name)

    def test_select_repository_falls_back_to_keyword_scoring(self) -> None:
        selected = select_repository(self.ticket, self.repos, ai_hint=None)
        self.assertEqual("org/backend-api", selected.full_name)

    def test_select_repository_ignores_non_matching_ai_hint(self) -> None:
        selected = select_repository(self.ticket, self.repos, ai_hint="org/unknown-repo")
        self.assertEqual("org/backend-api", selected.full_name)

    def test_select_repository_raises_when_candidates_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "No repository candidates configured"):
            select_repository(self.ticket, [], ai_hint=None)

    def test_select_repository_returns_first_candidate_when_no_keywords_match(self) -> None:
        ticket = Ticket(
            id="none",
            title="Unrelated task",
            description="No matching words here.",
            labels=[],
        )
        selected = select_repository(ticket, self.repos, ai_hint=None)
        self.assertEqual("org/frontend-app", selected.full_name)


class BuildIssueBodyTests(unittest.TestCase):
    def test_build_issue_body_contains_ticket_fields(self) -> None:
        ticket = Ticket(
            id="xyz789",
            title="Implement caching",
            description="Cache expensive query.",
            labels=["performance"],
        )
        body = build_issue_body(ticket)
        self.assertIn("Ticket ID: xyz789", body)
        self.assertIn("Title: Implement caching", body)
        self.assertIn("Labels: performance", body)
        self.assertIn("Cache expensive query.", body)

    def test_build_issue_body_uses_empty_description_fallback(self) -> None:
        ticket = Ticket(
            id="d0",
            title="No description",
            description="   ",
            labels=[],
        )
        body = build_issue_body(ticket)
        self.assertIn("(no description provided)", body)


_BASE_ENV = {
    "TRELLO_API_KEY": "key",
    "TRELLO_TOKEN": "tok",
    "TRELLO_TODO_LIST_ID": "todo-list",
    "TRELLO_DOING_LIST_ID": "doing-list",
    "GITHUB_TOKEN": "gh-tok",
    "REPO_CATALOG_JSON": '[{"full_name": "org/repo", "keywords": []}]',
}

_SAMPLE_CARD = {
    "id": "card-1",
    "shortLink": "sl1",
    "name": "Fix bug",
    "desc": "Some description",
    "labels": [],
}

_SAMPLE_CARD_2 = {
    "id": "card-2",
    "shortLink": "sl2",
    "name": "Add feature",
    "desc": "",
    "labels": [],
}


class RunTodoToDoingTests(unittest.TestCase):
    def _run_with_env(self, extra_env: dict | None = None):
        env = {**_BASE_ENV, **(extra_env or {})}
        with patch.dict(os.environ, env, clear=True):
            return run()

    @patch("automation.orchestrator.find_related_pr", return_value=None)
    @patch("automation.orchestrator.move_card_to_list")
    @patch("automation.orchestrator.fetch_trello_cards", return_value=[_SAMPLE_CARD])
    def test_moves_first_todo_card_to_doing(self, mock_fetch, mock_move, mock_pr):
        result = self._run_with_env()
        self.assertEqual(0, result)
        mock_move.assert_called_once_with("card-1", "doing-list", key="key", token="tok")

    @patch("automation.orchestrator.move_card_to_list")
    @patch("automation.orchestrator.fetch_trello_cards", return_value=[])
    def test_does_nothing_when_todo_list_is_empty(self, mock_fetch, mock_move):
        result = self._run_with_env()
        self.assertEqual(0, result)
        mock_move.assert_not_called()

    @patch("automation.orchestrator.find_related_pr", return_value=None)
    @patch("automation.orchestrator.move_card_to_list")
    @patch("automation.orchestrator.fetch_trello_cards", return_value=[_SAMPLE_CARD, _SAMPLE_CARD_2])
    def test_moves_only_first_card_when_multiple_todo_cards(self, mock_fetch, mock_move, mock_pr):
        self._run_with_env()
        # Only the first card should be moved to DOING
        doing_calls = [c for c in mock_move.call_args_list if c.args[1] == "doing-list"]
        self.assertEqual(1, len(doing_calls))
        self.assertEqual("card-1", doing_calls[0].args[0])

    @patch("automation.orchestrator.send_email_notification")
    @patch("automation.orchestrator.find_related_pr", return_value="https://github.com/org/repo/pull/1")
    @patch("automation.orchestrator.move_card_to_list")
    @patch("automation.orchestrator.fetch_trello_cards", return_value=[_SAMPLE_CARD, _SAMPLE_CARD_2])
    def test_card_moved_to_doing_is_skipped_in_done_loop(self, mock_fetch, mock_move, mock_pr, mock_email):
        self._run_with_env({"TRELLO_DONE_LIST_ID": "done-list"})
        done_calls = [c for c in mock_move.call_args_list if c.args[1] == "done-list"]
        # card-1 (moved to DOING) must not appear in done calls
        done_card_ids = [c.args[0] for c in done_calls]
        self.assertNotIn("card-1", done_card_ids)
        # card-2 (remaining TODO card with a PR) should be moved to DONE
        self.assertIn("card-2", done_card_ids)

    @patch("automation.orchestrator.find_related_pr", return_value="https://github.com/org/repo/pull/1")
    @patch("automation.orchestrator.send_email_notification")
    @patch("automation.orchestrator.move_card_to_list")
    @patch("automation.orchestrator.fetch_trello_cards", return_value=[_SAMPLE_CARD])
    def test_does_not_move_to_done_when_done_list_id_absent(self, mock_fetch, mock_move, mock_email, mock_pr):
        self._run_with_env()  # no TRELLO_DONE_LIST_ID
        done_calls = [c for c in mock_move.call_args_list if c.args[1] == "done-list"]
        self.assertEqual(0, len(done_calls))


if __name__ == "__main__":
    unittest.main()
