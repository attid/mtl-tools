from __future__ import annotations

import html
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Protocol

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from loguru import logger

from other.grist_tools import GristTableConfig, MTLGrist, grist_manager


class GristManagerProtocol(Protocol):
    async def load_table_data(
        self, table: GristTableConfig, sort: str | None = None, filter_dict: dict[str, list[Any]] | None = None
    ) -> list[dict[str, Any]]: ...

    async def post_data(self, table: GristTableConfig, json_data: dict[str, Any]) -> bool: ...

    async def patch_data(self, table: GristTableConfig, json_data: dict[str, Any]) -> bool: ...


@dataclass(frozen=True)
class SyncIssue:
    kind: str
    detail: str
    media_id: int | None = None
    media_name: str | None = None


@dataclass
class MtlAdminsSyncResult:
    created: int = 0
    updated: int = 0
    team_created: int = 0
    team_updated: int = 0
    media_checked: int = 0
    media_skipped: int = 0
    topics_checked: int = 0
    issues: list[SyncIssue] = field(default_factory=list)


def normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    normalized = username.strip().lstrip("@").lower()
    if not normalized:
        return None
    return f"@{normalized}"


def reference_list(ids: set[int] | list[int]) -> list[Any]:
    return ["L", *sorted(ids)]


class MtlAdminsSyncService:
    def __init__(self, grist_manager: GristManagerProtocol = grist_manager):
        self.grist_manager = grist_manager

    def resolve_media_target(self, media: dict[str, Any]) -> tuple[int | None, SyncIssue | None]:
        media_id = media.get("id")
        media_name = media.get("Name")
        raw_tgid = media.get("TgId")
        if raw_tgid in (None, ""):
            return None, SyncIssue("missing_tgid", "нужен Media.TgId", media_id=media_id, media_name=media_name)

        try:
            if isinstance(raw_tgid, float) and not raw_tgid.is_integer():
                raise ValueError
            return int(raw_tgid), None
        except (TypeError, ValueError):
            return (
                None,
                SyncIssue(
                    "invalid_tgid", f"некорректный Media.TgId: {raw_tgid}", media_id=media_id, media_name=media_name
                ),
            )

    async def sync(self, bot: Any, admin_service: Any | None = None) -> MtlAdminsSyncResult:
        result = MtlAdminsSyncResult()
        media_rows = await self.grist_manager.load_table_data(MTLGrist.MTL_ADMINS_MEDIA)
        admin_rows = await self.grist_manager.load_table_data(MTLGrist.MTL_ADMINS)
        topic_rows = await self.grist_manager.load_table_data(MTLGrist.MTL_ADMINS_AGORA_TOPICS)
        team_rows = await self.grist_manager.load_table_data(MTLGrist.MTL_ADMINS_AGORA_TEAM)

        owner_refs: dict[str, set[int]] = defaultdict(set)
        admin_refs: dict[str, set[int]] = defaultdict(set)
        display_usernames: dict[str, str] = {}

        for media in media_rows:
            if not self._is_telegram_media(media):
                continue

            media_id = self._int_or_none(media.get("id"))
            if media_id is None:
                result.media_skipped += 1
                result.issues.append(SyncIssue("invalid_media_id", f"invalid Media row id: {media.get('id')}"))
                continue

            target, issue = self.resolve_media_target(media)
            if issue:
                result.media_skipped += 1
                result.issues.append(issue)
                continue

            result.media_checked += 1
            try:
                telegram_admins = await bot.get_chat_administrators(chat_id=target)
            except (TelegramBadRequest, TelegramForbiddenError) as exc:
                result.issues.append(
                    SyncIssue(
                        "chat_unavailable",
                        f"чат {target} недоступен: {exc}",
                        media_id=media_id,
                        media_name=media.get("Name"),
                    )
                )
                continue
            except Exception as exc:
                logger.exception("Failed to fetch Telegram admins for {}", target)
                result.issues.append(
                    SyncIssue(
                        "telegram_error",
                        f"чат {target} недоступен: {type(exc).__name__}: {exc}",
                        media_id=media_id,
                        media_name=media.get("Name"),
                    )
                )
                continue

            for member in telegram_admins:
                user = getattr(member, "user", None)
                username = normalize_username(getattr(user, "username", None))
                if username is None:
                    user_id = getattr(user, "id", "unknown")
                    result.issues.append(
                        SyncIssue(
                            "admin_without_username",
                            f"admin id={user_id} has no username",
                            media_id=media_id,
                            media_name=media.get("Name"),
                        )
                    )
                    continue

                display_usernames.setdefault(username, username)
                status = str(getattr(member, "status", ""))
                if status in {"creator", "owner"}:
                    owner_refs[username].add(media_id)
                elif status == "administrator":
                    admin_refs[username].add(media_id)

        topic_refs = self._collect_topic_refs(admin_service, topic_rows, result)
        for username in topic_refs:
            display_usernames.setdefault(username, username)

        touched_usernames = set(owner_refs) | set(admin_refs) | set(topic_refs)
        admin_rows_by_username = await self._ensure_admin_rows(admin_rows, touched_usernames, display_usernames, result)

        await self._patch_admin_rows(admin_rows_by_username, owner_refs, admin_refs, result)
        await self._sync_topic_rows(team_rows, admin_rows_by_username, topic_refs, result)

        return result

    def _is_telegram_media(self, media: dict[str, Any]) -> bool:
        platform = str(media.get("Platform") or "").strip().lower()
        return platform == "telegram" or media.get("TgId") not in (None, "")

    async def _ensure_admin_rows(
        self,
        admin_rows: list[dict[str, Any]],
        usernames: set[str],
        display_usernames: dict[str, str],
        result: MtlAdminsSyncResult,
    ) -> dict[str, dict[str, Any]]:
        by_username, duplicate_usernames = self._admin_rows_by_username(admin_rows, result)
        missing = sorted(
            username for username in usernames if username not in by_username and username not in duplicate_usernames
        )

        if missing:
            await self.grist_manager.post_data(
                MTLGrist.MTL_ADMINS,
                {
                    "records": [
                        {"fields": {"Username": display_usernames.get(username, username), "Up_to_Date": True}}
                        for username in missing
                    ]
                },
            )
            result.created += len(missing)
            admin_rows = await self.grist_manager.load_table_data(MTLGrist.MTL_ADMINS)
            by_username, _duplicate_usernames = self._admin_rows_by_username(admin_rows, result)

        return by_username

    def _admin_rows_by_username(
        self, admin_rows: list[dict[str, Any]], result: MtlAdminsSyncResult
    ) -> tuple[dict[str, dict[str, Any]], set[str]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in admin_rows:
            username = normalize_username(row.get("Username"))
            if username:
                grouped[username].append(row)

        rows: dict[str, dict[str, Any]] = {}
        duplicate_usernames = set()
        for username, items in grouped.items():
            if len(items) > 1:
                duplicate_usernames.add(username)
                result.issues.append(SyncIssue("duplicate_admin_record", f"duplicate MTL_Admins username {username}"))
                continue
            rows[username] = items[0]
        return rows, duplicate_usernames

    async def _patch_admin_rows(
        self,
        admin_rows_by_username: dict[str, dict[str, Any]],
        owner_refs: dict[str, set[int]],
        admin_refs: dict[str, set[int]],
        result: MtlAdminsSyncResult,
    ) -> None:
        records = []
        for username in sorted(set(owner_refs) | set(admin_refs)):
            row = admin_rows_by_username.get(username)
            if not row:
                result.issues.append(SyncIssue("missing_admin_record", f"no MTL_Admins row for {username}"))
                continue
            records.append(
                {
                    "id": row["id"],
                    "fields": {
                        "As_Owner": reference_list(owner_refs.get(username, set())),
                        "As_Admin": reference_list(admin_refs.get(username, set())),
                        "Up_to_Date": True,
                    },
                }
            )

        if records:
            result.updated += len(records)
            await self.grist_manager.patch_data(MTLGrist.MTL_ADMINS, {"records": records})

    def _collect_topic_refs(
        self, admin_service: Any | None, topic_rows: list[dict[str, Any]], result: MtlAdminsSyncResult
    ) -> dict[str, set[int]]:
        topic_refs: dict[str, set[int]] = defaultdict(set)
        if not admin_service or not hasattr(admin_service, "get_all_topic_admins"):
            return topic_refs

        topics_by_id = self._topics_by_thread_id(topic_rows)
        for topic_key, usernames in admin_service.get_all_topic_admins().items():
            thread_id = self._topic_thread_id(topic_key)
            if thread_id is None:
                result.issues.append(SyncIssue("invalid_topic_key", f"invalid topic key {topic_key}"))
                continue
            result.topics_checked += 1
            topic_row = topics_by_id.get(thread_id)
            if not topic_row:
                result.issues.append(
                    SyncIssue("missing_agora_topic", f"Topic {thread_id}: no matching MTLA_Agora_Topics row")
                )
                continue
            topic_record_id = self._int_or_none(topic_row.get("id"))
            if topic_record_id is None:
                result.issues.append(
                    SyncIssue("invalid_agora_topic", f"Topic {thread_id}: invalid MTLA_Agora_Topics row id")
                )
                continue
            for raw_username in usernames:
                username = normalize_username(raw_username)
                if not username:
                    result.issues.append(
                        SyncIssue("topic_admin_without_username", f"Topic {thread_id}: empty username")
                    )
                    continue
                topic_refs[username].add(topic_record_id)
        return topic_refs

    def _topics_by_thread_id(self, topic_rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        topics = {}
        for row in topic_rows:
            topic_id = row.get("Topic_Id") or self._topic_id_from_link(row.get("Link"))
            if topic_id is None:
                continue
            try:
                topics[int(topic_id)] = row
            except (TypeError, ValueError):
                continue
        return topics

    def _int_or_none(self, value: Any) -> int | None:
        try:
            if isinstance(value, float) and not value.is_integer():
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _topic_id_from_link(self, link: str | None) -> int | None:
        if not link:
            return None
        try:
            return int(str(link).rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            return None

    def _topic_thread_id(self, topic_key: str) -> int | None:
        try:
            return int(str(topic_key).rsplit("-", 1)[-1])
        except ValueError:
            return None

    async def _sync_topic_rows(
        self,
        team_rows: list[dict[str, Any]],
        admin_rows_by_username: dict[str, dict[str, Any]],
        topic_refs: dict[str, set[int]],
        result: MtlAdminsSyncResult,
    ) -> None:
        team_by_admin_id, duplicate_team_admin_ids = self._team_rows_by_admin_id(team_rows, result)
        create_records = []
        patch_records = []

        for username, topic_ids in sorted(topic_refs.items()):
            admin_row = admin_rows_by_username.get(username)
            if not admin_row:
                result.issues.append(
                    SyncIssue("missing_topic_admin_record", f"no MTL_Admins row for topic admin {username}")
                )
                continue
            admin_id = admin_row["id"]
            if admin_id in duplicate_team_admin_ids:
                continue
            fields = {"Topics_From_SkyNet": reference_list(topic_ids)}
            team_row = team_by_admin_id.get(admin_id)
            if team_row:
                patch_records.append({"id": team_row["id"], "fields": fields})
            else:
                create_records.append({"fields": {"Username": admin_id, **fields}})

        if create_records:
            await self.grist_manager.post_data(MTLGrist.MTL_ADMINS_AGORA_TEAM, {"records": create_records})
            result.team_created += len(create_records)
        if patch_records:
            await self.grist_manager.patch_data(MTLGrist.MTL_ADMINS_AGORA_TEAM, {"records": patch_records})
            result.team_updated += len(patch_records)

    def _team_rows_by_admin_id(
        self, team_rows: list[dict[str, Any]], result: MtlAdminsSyncResult
    ) -> tuple[dict[int, dict[str, Any]], set[int]]:
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in team_rows:
            admin_id = row.get("Username")
            if isinstance(admin_id, int):
                grouped[admin_id].append(row)

        rows = {}
        duplicate_admin_ids = set()
        for admin_id, items in grouped.items():
            if len(items) > 1:
                duplicate_admin_ids.add(admin_id)
                result.issues.append(
                    SyncIssue("duplicate_agora_team", f"duplicate MTLA_Agora_Team Username={admin_id}")
                )
                continue
            rows[admin_id] = items[0]
        return rows, duplicate_admin_ids


def chunk_text(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            chunks.append(current.rstrip())
            current = ""
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        current += line
    if current:
        chunks.append(current.rstrip())
    return chunks


def format_sync_report(result: MtlAdminsSyncResult) -> str:
    lines = [
        "MTL admins sync completed.",
        f"Media checked: {result.media_checked}",
        f"Media skipped: {result.media_skipped}",
        f"Admin records created: {result.created}",
        f"Admin records updated: {result.updated}",
        f"Agora team records created: {result.team_created}",
        f"Agora team records updated: {result.team_updated}",
        "",
        "Problems:",
    ]
    if not result.issues:
        lines.append("none")
    else:
        for issue in result.issues:
            prefix = ""
            if issue.media_id is not None:
                media_name = html.escape(str(issue.media_name or ""))
                prefix = f"Media #{issue.media_id} {media_name}: "
            lines.append(f"- {prefix}{html.escape(issue.detail)}")
    return "\n".join(lines)
