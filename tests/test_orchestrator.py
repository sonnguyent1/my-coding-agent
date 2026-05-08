import unittest

from automation.orchestrator import RepoCandidate, Ticket, build_issue_body, select_repository


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


if __name__ == "__main__":
    unittest.main()

