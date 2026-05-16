from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True)
class TrelloAgent:
    name: str | None
    conversation_id: str | None


@dataclass(frozen=True)
class TrelloBadgeAttachmentsByType:
    board: int
    card: int


@dataclass(frozen=True)
class TrelloBadgeAttachments:
    trello: TrelloBadgeAttachmentsByType


@dataclass(frozen=True)
class TrelloBadges:
    attachments: int
    fogbugz: str
    check_items: int
    check_items_checked: int
    check_items_earliest_due: str | None
    comments: int
    description: bool
    due: str | None
    due_complete: bool
    last_updated_by_ai: bool
    start: str | None
    external_source: str | None
    attachments_by_type: TrelloBadgeAttachments
    location: bool
    votes: int
    malicious_attachments: int
    viewing_member_voted: bool
    subscribed: bool


@dataclass(frozen=True)
class TrelloCoverScaled:
    id: str
    original_id: str
    scaled: bool
    url: str
    bytes: int
    height: int
    width: int


@dataclass(frozen=True)
class TrelloCover:
    id_attachment: str | None
    color: str | None
    id_uploaded_background: str | None
    size: str
    brightness: str
    y_position: float
    scaled: list[TrelloCoverScaled]
    edge_color: str | None
    id_plugin: str | None


@dataclass(frozen=True)
class TrelloCard:
    id: str
    agent: TrelloAgent
    badges: TrelloBadges
    check_item_states: list[dict[str, Any]]
    closed: bool
    due_complete: bool
    date_last_activity: str
    desc: str
    due: str | None
    due_reminder: int | None
    email: str | None
    id_board: str
    id_checklists: list[str]
    id_list: str
    id_members: list[str]
    id_members_voted: list[str]
    id_short: int
    id_attachment_cover: str | None
    labels: list[dict[str, Any]]
    id_labels: list[str]
    manual_cover_attachment: bool
    name: str
    node_id: str
    pinned: bool
    pos: int | float
    short_link: str
    short_url: str
    start: str | None
    subscribed: bool
    url: str
    cover: TrelloCover
    is_template: bool
    card_role: str | None
    mirror_source_id: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloCard:
        agent_payload = payload.get("agent") or {}
        badges_payload = payload.get("badges") or {}
        attachments_by_type_payload = badges_payload.get("attachmentsByType") or {}
        trello_attachment_payload = attachments_by_type_payload.get("trello") or {}
        cover_payload = payload.get("cover") or {}
        cover_scaled_payload = cover_payload.get("scaled") or []

        return cls(
            id=payload.get("id", ""),
            agent=TrelloAgent(
                name=agent_payload.get("name"),
                conversation_id=agent_payload.get("conversationId"),
            ),
            badges=TrelloBadges(
                attachments=int(badges_payload.get("attachments", 0)),
                fogbugz=badges_payload.get("fogbugz", ""),
                check_items=int(badges_payload.get("checkItems", 0)),
                check_items_checked=int(badges_payload.get("checkItemsChecked", 0)),
                check_items_earliest_due=badges_payload.get("checkItemsEarliestDue"),
                comments=int(badges_payload.get("comments", 0)),
                description=bool(badges_payload.get("description", False)),
                due=badges_payload.get("due"),
                due_complete=bool(badges_payload.get("dueComplete", False)),
                last_updated_by_ai=bool(badges_payload.get("lastUpdatedByAi", False)),
                start=badges_payload.get("start"),
                external_source=badges_payload.get("externalSource"),
                attachments_by_type=TrelloBadgeAttachments(
                    trello=TrelloBadgeAttachmentsByType(
                        board=int(trello_attachment_payload.get("board", 0)),
                        card=int(trello_attachment_payload.get("card", 0)),
                    )
                ),
                location=bool(badges_payload.get("location", False)),
                votes=int(badges_payload.get("votes", 0)),
                malicious_attachments=int(badges_payload.get("maliciousAttachments", 0)),
                viewing_member_voted=bool(badges_payload.get("viewingMemberVoted", False)),
                subscribed=bool(badges_payload.get("subscribed", False)),
            ),
            check_item_states=payload.get("checkItemStates") or [],
            closed=bool(payload.get("closed", False)),
            due_complete=bool(payload.get("dueComplete", False)),
            date_last_activity=payload.get("dateLastActivity", ""),
            desc=payload.get("desc", ""),
            due=payload.get("due"),
            due_reminder=payload.get("dueReminder"),
            email=payload.get("email"),
            id_board=payload.get("idBoard", ""),
            id_checklists=payload.get("idChecklists") or [],
            id_list=payload.get("idList", ""),
            id_members=payload.get("idMembers") or [],
            id_members_voted=payload.get("idMembersVoted") or [],
            id_short=int(payload.get("idShort", 0)),
            id_attachment_cover=payload.get("idAttachmentCover"),
            labels=payload.get("labels") or [],
            id_labels=payload.get("idLabels") or [],
            manual_cover_attachment=bool(payload.get("manualCoverAttachment", False)),
            name=payload.get("name", ""),
            node_id=payload.get("nodeId", ""),
            pinned=bool(payload.get("pinned", False)),
            pos=payload.get("pos", 0),
            short_link=payload.get("shortLink", ""),
            short_url=payload.get("shortUrl", ""),
            start=payload.get("start"),
            subscribed=bool(payload.get("subscribed", False)),
            url=payload.get("url", ""),
            cover=TrelloCover(
                id_attachment=cover_payload.get("idAttachment"),
                color=cover_payload.get("color"),
                id_uploaded_background=cover_payload.get("idUploadedBackground"),
                size=cover_payload.get("size", "normal"),
                brightness=cover_payload.get("brightness", "dark"),
                y_position=float(cover_payload.get("yPosition", 0.5)),
                scaled=[
                    TrelloCoverScaled(
                        id=item.get("id", ""),
                        original_id=item.get("_id", ""),
                        scaled=bool(item.get("scaled", False)),
                        url=item.get("url", ""),
                        bytes=int(item.get("bytes", 0)),
                        height=int(item.get("height", 0)),
                        width=int(item.get("width", 0)),
                    )
                    for item in cover_scaled_payload
                ],
                edge_color=cover_payload.get("edgeColor"),
                id_plugin=cover_payload.get("idPlugin"),
            ),
            is_template=bool(payload.get("isTemplate", False)),
            card_role=payload.get("cardRole"),
            mirror_source_id=payload.get("mirrorSourceId"),
        )


@dataclass(frozen=True)
class TrelloAttachmentPreview:
    id: str
    original_id: str
    scaled: bool
    url: str
    bytes: int
    height: int
    width: int

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloAttachmentPreview:
        return cls(
            id=payload.get("id", ""),
            original_id=payload.get("_id", ""),
            scaled=bool(payload.get("scaled", False)),
            url=payload.get("url", ""),
            bytes=int(payload.get("bytes", 0)),
            height=int(payload.get("height", 0)),
            width=int(payload.get("width", 0)),
        )


@dataclass(frozen=True)
class TrelloAttachment:
    id: str
    bytes: int
    date: str
    edge_color: str | None
    id_member: str
    is_malicious: bool
    is_upload: bool
    mime_type: str
    name: str
    file_name: str
    previews: list[TrelloAttachmentPreview]
    source_view: str | None
    url: str
    pos: int | float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloAttachment:
        return cls(
            id=payload.get("id", ""),
            bytes=int(payload.get("bytes", 0)),
            date=payload.get("date", ""),
            edge_color=payload.get("edgeColor"),
            id_member=payload.get("idMember", ""),
            is_malicious=bool(payload.get("isMalicious", False)),
            is_upload=bool(payload.get("isUpload", False)),
            mime_type=payload.get("mimeType", ""),
            name=payload.get("name", ""),
            file_name=payload.get("fileName", ""),
            previews=[
                TrelloAttachmentPreview.from_dict(item)
                for item in (payload.get("previews") or [])
            ],
            source_view=payload.get("sourceView"),
            url=payload.get("url", ""),
            pos=payload.get("pos", 0),
        )

    @classmethod
    def list_from_dict(cls, payload: list[dict[str, Any]]) -> list[TrelloAttachment]:
        return [cls.from_dict(item) for item in payload]


@dataclass(frozen=True)
class TrelloCheckItem:
    id: str
    name: str
    name_data: dict[str, Any]
    pos: int | float
    state: str
    due: str | None
    due_reminder: int | None
    id_member: str | None
    id_checklist: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloCheckItem:
        return cls(
            id=payload.get("id", ""),
            name=payload.get("name", ""),
            name_data=payload.get("nameData") or {},
            pos=payload.get("pos", 0),
            state=payload.get("state", "incomplete"),
            due=payload.get("due"),
            due_reminder=payload.get("dueReminder"),
            id_member=payload.get("idMember"),
            id_checklist=payload.get("idChecklist", ""),
        )

    @classmethod
    def list_from_dict(cls, payload: list[dict[str, Any]]) -> list[TrelloCheckItem]:
        return [cls.from_dict(item) for item in payload]

    @classmethod
    def list_from_checklists(cls, payload: list[dict[str, Any]]) -> list[TrelloCheckItem]:
        check_items: list[TrelloCheckItem] = []
        for checklist in payload:
            check_items.extend(cls.list_from_dict(checklist.get("checkItems") or []))
        return check_items


@dataclass(frozen=True)
class TrelloCommentCardRef:
    id: str
    name: str
    id_short: int
    short_link: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloCommentCardRef:
        return cls(
            id=payload.get("id", ""),
            name=payload.get("name", ""),
            id_short=int(payload.get("idShort", 0)),
            short_link=payload.get("shortLink", ""),
        )


@dataclass(frozen=True)
class TrelloCommentBoardRef:
    id: str
    name: str
    short_link: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloCommentBoardRef:
        return cls(
            id=payload.get("id", ""),
            name=payload.get("name", ""),
            short_link=payload.get("shortLink", ""),
        )


@dataclass(frozen=True)
class TrelloCommentListRef:
    id: str
    name: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloCommentListRef:
        return cls(
            id=payload.get("id", ""),
            name=payload.get("name", ""),
        )


@dataclass(frozen=True)
class TrelloCommentData:
    id_card: str
    id_author: str
    text: str
    text_data: dict[str, Any]
    card: TrelloCommentCardRef
    board: TrelloCommentBoardRef
    list_ref: TrelloCommentListRef

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloCommentData:
        return cls(
            id_card=payload.get("idCard", ""),
            id_author=payload.get("idAuthor", ""),
            text=payload.get("text", ""),
            text_data=payload.get("textData") or {},
            card=TrelloCommentCardRef.from_dict(payload.get("card") or {}),
            board=TrelloCommentBoardRef.from_dict(payload.get("board") or {}),
            list_ref=TrelloCommentListRef.from_dict(payload.get("list") or {}),
        )


@dataclass(frozen=True)
class TrelloMemberCreator:
    id: str
    full_name: str
    username: str
    initials: str
    avatar_hash: str | None
    avatar_url: str | None
    activity_blocked: bool
    id_member_referrer: str | None
    non_public: dict[str, Any]
    non_public_available: bool

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloMemberCreator:
        return cls(
            id=payload.get("id", ""),
            full_name=payload.get("fullName", ""),
            username=payload.get("username", ""),
            initials=payload.get("initials", ""),
            avatar_hash=payload.get("avatarHash"),
            avatar_url=payload.get("avatarUrl"),
            activity_blocked=bool(payload.get("activityBlocked", False)),
            id_member_referrer=payload.get("idMemberReferrer"),
            non_public=payload.get("nonPublic") or {},
            non_public_available=bool(payload.get("nonPublicAvailable", False)),
        )


@dataclass(frozen=True)
class TrelloComment:
    id: str
    id_member_creator: str
    data: TrelloCommentData
    app_creator: dict[str, Any] | None
    type: str
    date: str
    limits: dict[str, Any]
    member_creator: TrelloMemberCreator

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrelloComment:
        return cls(
            id=payload.get("id", ""),
            id_member_creator=payload.get("idMemberCreator", ""),
            data=TrelloCommentData.from_dict(payload.get("data") or {}),
            app_creator=payload.get("appCreator"),
            type=payload.get("type", ""),
            date=payload.get("date", ""),
            limits=payload.get("limits") or {},
            member_creator=TrelloMemberCreator.from_dict(payload.get("memberCreator") or {}),
        )

    @classmethod
    def list_from_dict(cls, payload: list[dict[str, Any]]) -> list[TrelloComment]:
        return [cls.from_dict(item) for item in payload]

@dataclass(frozen=True)
class CardInformation:
    card_name: str
    card_description: str
    
    card: TrelloCard
    attachments: list[TrelloAttachment]
    checkitems: list[TrelloCheckItem]   
