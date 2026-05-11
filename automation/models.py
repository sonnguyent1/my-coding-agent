from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    id: str
    title: str
    description: str
    labels: list[str]


@dataclass(frozen=True)
class RepoCandidate:
    full_name: str
    keywords: list[str]
