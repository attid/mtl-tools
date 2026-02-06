"""
Stellar notification service for handling operations webhooks from operations-notifier.

This service replaces the polling mechanism with webhook-based notifications.
"""

import asyncio
import json
from collections import OrderedDict
from typing import Any
from urllib.parse import quote

import aiohttp
from aiohttp import web
from loguru import logger

from other.config_reader import config
from other.grist_tools import grist_manager, MTLGrist
from other.stellar.address_utils import shorten_address
from other.utils import float2str

SAFE = "-_.!~*'()"


class StellarNotificationService:
    """Service for receiving and processing Stellar operation notifications via webhooks."""

    def __init__(self, bot: Any, session_pool: Any):
        """
        Initialize the notification service.

        Args:
            bot: Telegram bot instance
            session_pool: SQLAlchemy session pool for database access
        """
        self.bot = bot
        self.session_pool = session_pool
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        # Deduplication: track notified operation IDs
        self.notified_operations: set[tuple[str, Any]] = set()
        self.max_cache_size = 1024

        # Mapping: subscription_id -> destination info
        # {subscription_id: {"chat_id": int, "topic_id": int, "type": str, "asset": str, "min": int}}
        self.subscriptions_map: dict[str, dict[str, Any]] = {}

        # Nonce for API calls
        self._nonce = 0
        self._nonce_lock = asyncio.Lock()

    # === Server Lifecycle ===

    async def start_server(self) -> None:
        """Start the webhook HTTP server."""
        if not config.notifier_url or not config.webhook_public_url:
            logger.warning("Notifier URL or webhook URL not configured, skipping webhook server")
            return

        if config.test_mode:
            logger.info("Test mode: Webhook server will not start")
            return

        app = web.Application()
        app.router.add_post("/webhook", self.handle_webhook)

        self.runner = web.AppRunner(app)
        await self.runner.setup()

        port = config.webhook_port
        self.site = web.TCPSite(self.runner, "0.0.0.0", port)

        logger.info(f"Starting Stellar webhook server on port {port}")
        await self.site.start()

    async def stop(self) -> None:
        """Stop the webhook server gracefully."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Stellar webhook server stopped")

    # === Webhook Handler ===

    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming webhook POST requests from operations-notifier.

        Args:
            request: aiohttp web request

        Returns:
            HTTP response
        """
        try:
            body_bytes = await request.read()
            if not body_bytes:
                return web.Response(text="Empty payload", status=400)

            try:
                payload = json.loads(body_bytes)
            except json.JSONDecodeError:
                return web.Response(text="Invalid JSON", status=400)

            subscription_id = request.headers.get("X-Subscription") or payload.get("subscription")
            logger.info(f"Webhook received (sub={subscription_id}): {json.dumps(payload)[:200]}")

            await self.process_notification(payload, subscription_id)
            return web.Response(text="OK")

        except Exception as e:
            logger.exception(f"Error handling webhook: {e}")
            return web.Response(text=f"Error: {e}", status=500)

    # === Notification Processing ===

    async def process_notification(self, payload: dict[str, Any], subscription_id: str | None = None) -> None:
        """
        Process a notification payload and send to appropriate Telegram chat.

        Args:
            payload: Inner payload from operations-notifier (contains operation, transaction)
            subscription_id: Subscription ID from the top-level webhook body
        """
        op_info = payload.get("operation", {})

        # Deduplicate by (operation_id, subscription_id)
        stellar_op_id = op_info.get("id")
        dedup_key = (stellar_op_id, subscription_id) if stellar_op_id else None
        if dedup_key:
            if dedup_key in self.notified_operations:
                logger.debug(f"Skipping duplicate operation {stellar_op_id} for subscription {subscription_id}")
                return
            self.notified_operations.add(dedup_key)
            # Clear cache if too large
            if len(self.notified_operations) > self.max_cache_size:
                self.notified_operations.clear()

        # Find destination from subscription map
        if not subscription_id:
            logger.warning("No subscription ID in payload, cannot route notification")
            return
        destination = self.subscriptions_map.get(subscription_id)
        if not destination:
            logger.warning(f"Unknown subscription {subscription_id}, cannot route notification")
            return

        # Check minimum amount filter
        min_amount = destination.get("min", 0)
        if min_amount > 0:
            amount = float(op_info.get("amount", 0))
            if amount < min_amount:
                logger.debug(f"Operation amount {amount} below minimum {min_amount}, skipping")
                return

        # Format and send message
        message = self._format_message(payload, destination)
        if message:
            logger.info(f"Sending notification to chat {destination['chat_id']}: {message[:100]}")
            await self._send_to_telegram(
                chat_id=destination["chat_id"],
                topic_id=destination.get("topic_id"),
                message=message
            )

    def _format_message(self, payload: dict[str, Any], destination: dict[str, Any]) -> str | None:
        """
        Format a webhook payload into a human-readable Telegram message.

        Args:
            payload: Webhook payload
            destination: Destination info with type context

        Returns:
            Formatted HTML message string or None
        """
        op = payload.get("operation", {})
        tx = payload.get("transaction", {})

        op_type = op.get("type", "unknown")
        op_id = op.get("id", "")

        # Build operation link
        link = f'https://viewer.eurmtl.me/operation/{op_id}'

        # Get account info
        source_account = op.get("source_account") or op.get("from") or op.get("account") or ""
        dest_account = op.get("to") or op.get("destination") or ""

        # Format based on operation type
        if op_type == "payment":
            amount = float2str(op.get("amount", 0))
            asset = self._get_asset_code(op.get("asset", {}))
            msg = (
                f'<a href="{link}">Операция</a> payment\n'
                f'От: {shorten_address(source_account)}\n'
                f'Кому: {shorten_address(dest_account)}\n'
                f'Сумма: {amount} {asset}'
            )

        elif op_type == "create_account":
            amount = float2str(op.get("amount", 0))
            msg = (
                f'<a href="{link}">Операция</a> create_account\n'
                f'От: {shorten_address(source_account)}\n'
                f'Новый аккаунт: {shorten_address(dest_account)}\n'
                f'Начальный баланс: {amount} XLM'
            )

        elif op_type in ("path_payment_strict_send", "path_payment_strict_receive"):
            sent_amount = float2str(op.get("source_amount") or op.get("amount", 0))
            sent_asset = self._get_asset_code(op.get("source_asset", {}))
            recv_amount = float2str(op.get("dest_amount") or op.get("amount", 0))
            recv_asset = self._get_asset_code(op.get("asset", {}))
            msg = (
                f'<a href="{link}">Операция</a> {op_type}\n'
                f'От: {shorten_address(source_account)}\n'
                f'Кому: {shorten_address(dest_account)}\n'
                f'Отправлено: {sent_amount} {sent_asset}\n'
                f'Получено: {recv_amount} {recv_asset}'
            )

        elif op_type in ("manage_sell_offer", "manage_buy_offer"):
            amount = float2str(op.get("amount", 0))
            price = float2str(op.get("price", 0))
            selling = self._get_asset_code(op.get("source_asset") or op.get("selling_asset", {}))
            buying = self._get_asset_code(op.get("asset") or op.get("buying_asset", {}))
            offer_id = op.get("offer_id") or op.get("created_offer_id", 0)
            msg = (
                f'<a href="{link}">Операция</a> {op_type}\n'
                f'Аккаунт: {shorten_address(source_account)}\n'
                f'Продажа: {amount} {selling}\n'
                f'Покупка: {buying} по цене {price}\n'
                f'Offer ID: {offer_id}'
            )

        elif op_type == "change_trust":
            asset = self._get_asset_code(op.get("asset", {}))
            limit = op.get("limit", "")
            msg = (
                f'<a href="{link}">Операция</a> change_trust\n'
                f'Аккаунт: {shorten_address(source_account)}\n'
                f'Токен: {asset}\n'
                f'Лимит: {limit}'
            )

        elif op_type == "set_trustline_flags":
            trustor = op.get("trustor", "")
            asset = self._get_asset_code(op.get("asset", {}))
            msg = (
                f'<a href="{link}">Операция</a> set_trustline_flags\n'
                f'Issuer: {shorten_address(source_account)}\n'
                f'Trustor: {shorten_address(trustor)}\n'
                f'Токен: {asset}'
            )

        else:
            # Generic format for other operation types
            msg = (
                f'<a href="{link}">Операция</a> {op_type}\n'
                f'Аккаунт: {shorten_address(source_account)}'
            )

        # Add memo if present
        memo_data = tx.get("memo", {})
        if memo_data:
            memo_type = memo_data.get("type")
            memo_value = memo_data.get("value")
            if memo_value:
                # Handle Buffer type memo
                if memo_type == "text" and isinstance(memo_value, dict) and "data" in memo_value:
                    try:
                        memo_bytes = bytes(memo_value.get("data", []))
                        memo_text = memo_bytes.decode("utf-8")
                    except Exception:
                        memo_text = "(binary data)"
                else:
                    memo_text = str(memo_value)
                msg += f'\nMemo: {memo_text}'

        return msg

    def _get_asset_code(self, asset: dict[str, Any] | None) -> str:
        """Extract asset code from asset object, defaulting to XLM for native."""
        if not asset:
            return "XLM"
        if asset.get("asset_type") in ("native", 0, "0"):
            return "XLM"
        return asset.get("asset_code", "XLM")

    async def _send_to_telegram(self, chat_id: int, topic_id: int | None, message: str) -> None:
        """
        Send a message to Telegram via the message queue (db).

        Args:
            chat_id: Telegram chat ID
            topic_id: Message thread ID for topics
            message: HTML-formatted message
        """
        from db.repositories import MessageRepository

        try:
            with self.session_pool() as session:
                repo = MessageRepository(session)
                repo.add_message(chat_id, message, topic_id=topic_id or 0)
                session.commit()
                logger.debug(f"Queued notification for chat {chat_id}")
        except Exception as e:
            logger.exception(f"Failed to queue notification: {e}")

    # === Subscription Management ===

    async def _get_next_nonce(self) -> int:
        """Get next sequential nonce for API calls."""
        async with self._nonce_lock:
            if self._nonce == 0:
                import time
                self._nonce = int(time.time() * 1000)
            self._nonce += 1
            return self._nonce

    def _encode_url_params(self, pairs: list[tuple[str, Any]]) -> str:
        """Encode parameters for URL query string."""
        pairs.sort(key=lambda x: x[0])
        parts = []
        for k, v in pairs:
            if isinstance(v, (list, tuple)):
                v = ",".join(str(x) for x in v)
            parts.append(f"{quote(str(k), safe=SAFE)}={quote(str(v), safe=SAFE)}")
        return "&".join(parts)

    async def subscribe_token(self, asset_code: str, asset_issuer: str) -> str | None:
        """
        Subscribe to notifications for a specific token/asset.

        Args:
            asset_code: Asset code (e.g., "MTL")
            asset_issuer: Asset issuer public key

        Returns:
            Subscription ID if successful, None otherwise
        """
        if not config.notifier_url or not config.webhook_public_url:
            return None

        url = f"{config.notifier_url}/api/subscription"
        webhook = config.webhook_public_url

        nonce = await self._get_next_nonce()
        pairs = [
            ("asset_code", asset_code),
            ("asset_issuer", asset_issuer),
            ("nonce", nonce),
            ("operation_types", [1]),
            ("reaction_url", webhook),
        ]

        body_json = json.dumps(OrderedDict(pairs), separators=(",", ":"))
        headers = self._get_auth_headers()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=body_json, headers=headers) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        subscription_id = data.get("id") or data.get("subscription_id")
                        logger.info(f"Subscribed to token {asset_code}: {subscription_id}")
                        return subscription_id
                    else:
                        text = await resp.text()
                        logger.error(f"Failed to subscribe to token {asset_code}: {resp.status} {text}")
                        return None
            except Exception as e:
                logger.exception(f"Exception subscribing to token {asset_code}: {e}")
                return None

    async def subscribe_account(self, account_id: str) -> str | None:
        """
        Subscribe to notifications for a specific account.

        Args:
            account_id: Stellar account public key

        Returns:
            Subscription ID if successful, None otherwise
        """
        if not config.notifier_url or not config.webhook_public_url:
            return None

        if not account_id or not account_id.startswith("G") or len(account_id) != 56:
            logger.warning(f"Invalid account ID: {account_id}")
            return None

        url = f"{config.notifier_url}/api/subscription"
        webhook = config.webhook_public_url

        nonce = await self._get_next_nonce()
        pairs = [
            ("account", account_id),
            ("nonce", nonce),
            ("reaction_url", webhook),
        ]

        body_json = json.dumps(OrderedDict(pairs), separators=(",", ":"))
        headers = self._get_auth_headers()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=body_json, headers=headers) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        subscription_id = data.get("id") or data.get("subscription_id")
                        logger.info(f"Subscribed to account {shorten_address(account_id)}: {subscription_id}")
                        return subscription_id
                    else:
                        text = await resp.text()
                        logger.error(
                            f"Failed to subscribe to account {shorten_address(account_id)}: {resp.status} {text}"
                        )
                        return None
            except Exception as e:
                logger.exception(f"Exception subscribing to account {shorten_address(account_id)}: {e}")
                return None

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a notification.

        Args:
            subscription_id: ID of the subscription to remove

        Returns:
            True if successful, False otherwise
        """
        if not config.notifier_url:
            return False

        url = f"{config.notifier_url}/api/subscription/{subscription_id}"
        nonce = await self._get_next_nonce()
        headers = self._get_auth_headers()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(f"{url}?nonce={nonce}", headers=headers) as resp:
                    if resp.status == 200:
                        logger.info(f"Unsubscribed: {subscription_id}")
                        self.subscriptions_map.pop(subscription_id, None)
                        return True
                    else:
                        text = await resp.text()
                        logger.error(f"Failed to unsubscribe {subscription_id}: {resp.status} {text}")
                        return False
            except Exception as e:
                logger.exception(f"Exception unsubscribing {subscription_id}: {e}")
                return False

    async def get_active_subscriptions(self) -> list[dict[str, Any]]:
        """
        Get list of active subscriptions from the notifier.

        Returns:
            List of subscription dicts with id and resource info
        """
        if not config.notifier_url:
            return []

        nonce = await self._get_next_nonce()
        headers = self._get_auth_headers()
        url = f"{config.notifier_url}/api/subscription?nonce={nonce}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return data
                        return []
                    else:
                        logger.error(f"Failed to get subscriptions: {resp.status} {await resp.text()}")
                        return []
            except Exception as e:
                logger.exception(f"Error fetching subscriptions: {e}")
                return []

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers for notifier API calls."""
        headers = {"Content-Type": "application/json"}
        if config.notifier_auth_token:
            headers["Authorization"] = config.notifier_auth_token
        return headers

    # === Grist Config Sync ===

    async def load_grist_config(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Load notification config from Grist tables.

        Returns:
            Tuple of (assets_config, accounts_config)
        """
        try:
            assets_config = await grist_manager.load_table_data(MTLGrist.NOTIFY_ASSETS)
            accounts_config = await grist_manager.load_table_data(MTLGrist.NOTIFY_ACCOUNTS)
            return assets_config, accounts_config
        except Exception as e:
            logger.exception(f"Failed to load Grist config: {e}")
            return [], []

    async def sync_subscriptions(self) -> None:
        """
        Synchronize subscriptions with Grist config.

        This method:
        1. Loads current config from Grist
        2. Gets active subscriptions from notifier
        3. Subscribes to new items
        4. Updates the subscriptions_map for routing
        """
        if not config.notifier_url or not config.webhook_public_url:
            logger.warning("Notifier not configured, skipping subscription sync")
            return

        if config.test_mode:
            logger.info("Test mode: Skipping subscription sync")
            return

        logger.info("Starting subscription sync...")

        try:
            # Load Grist config
            assets_config, accounts_config = await self.load_grist_config()

            # Get current subscriptions from notifier
            current_subs = await self.get_active_subscriptions()
            current_sub_resources: set[str] = set()
            current_sub_map: dict[str, str] = {}  # resource -> subscription_id

            current_sub_details: dict[str, dict[str, Any]] = {}  # resource -> full sub dict

            for sub in current_subs:
                sub_id = sub.get("id") or sub.get("subscription_id")
                # Resource can be account or asset
                resource = sub.get("account") or sub.get("resource_id")
                if sub.get("asset_code") and sub.get("asset_issuer"):
                    resource = f"{sub['asset_code']}-{sub['asset_issuer']}"
                if resource and sub_id:
                    current_sub_resources.add(resource)
                    current_sub_map[resource] = sub_id
                    current_sub_details[resource] = sub

            # Process asset subscriptions
            for asset_cfg in assets_config:
                if not asset_cfg.get("enabled"):
                    continue

                asset = asset_cfg.get("asset", "")
                if "-" not in asset:
                    continue

                asset_code, asset_issuer = asset.split("-", 1)
                resource_key = f"{asset_code}-{asset_issuer}"

                chat_id = int(asset_cfg.get("chat_id", 0))
                topic_id = asset_cfg.get("topic_id")
                min_amount = int(asset_cfg.get("min", 0))

                if resource_key in current_sub_resources:
                    # Check if existing subscription has correct operation_types filter
                    existing_sub = current_sub_details.get(resource_key, {})
                    existing_op_types = existing_sub.get("operation_types")
                    if existing_op_types != [1]:
                        # Recreate subscription with payment-only filter
                        old_sub_id = current_sub_map[resource_key]
                        logger.info(f"Recreating asset subscription {asset_code}: operation_types {existing_op_types} -> [1]")
                        await self.unsubscribe(old_sub_id)
                        await asyncio.sleep(0.1)
                        sub_id = await self.subscribe_token(asset_code, asset_issuer)
                        if sub_id:
                            self.subscriptions_map[sub_id] = {
                                "chat_id": chat_id,
                                "topic_id": topic_id,
                                "type": "asset",
                                "asset": asset,
                                "min": min_amount,
                            }
                    else:
                        # Already subscribed with correct filter, just update map
                        sub_id = current_sub_map[resource_key]
                        self.subscriptions_map[sub_id] = {
                            "chat_id": chat_id,
                            "topic_id": topic_id,
                            "type": "asset",
                            "asset": asset,
                            "min": min_amount,
                        }
                        logger.debug(f"Asset {asset_code} already subscribed: {sub_id}")
                else:
                    # Need to subscribe
                    sub_id = await self.subscribe_token(asset_code, asset_issuer)
                    if sub_id:
                        self.subscriptions_map[sub_id] = {
                            "chat_id": chat_id,
                            "topic_id": topic_id,
                            "type": "asset",
                            "asset": asset,
                            "min": min_amount,
                        }
                    await asyncio.sleep(0.1)  # Rate limiting

            # Process account subscriptions
            for account_cfg in accounts_config:
                if not account_cfg.get("enabled"):
                    continue

                account_id = account_cfg.get("account_id", "")
                if not account_id or not account_id.startswith("G"):
                    continue

                chat_id = int(account_cfg.get("chat_id", 0))
                topic_id = account_cfg.get("topic_id")

                if account_id in current_sub_resources:
                    # Already subscribed, just update map
                    sub_id = current_sub_map[account_id]
                    self.subscriptions_map[sub_id] = {
                        "chat_id": chat_id,
                        "topic_id": topic_id,
                        "type": "account",
                        "account_id": account_id,
                        "min": 0,
                    }
                    logger.debug(f"Account {shorten_address(account_id)} already subscribed: {sub_id}")
                else:
                    # Need to subscribe
                    sub_id = await self.subscribe_account(account_id)
                    if sub_id:
                        self.subscriptions_map[sub_id] = {
                            "chat_id": chat_id,
                            "topic_id": topic_id,
                            "type": "account",
                            "account_id": account_id,
                            "min": 0,
                        }
                    await asyncio.sleep(0.1)  # Rate limiting

            logger.info(
                f"Subscription sync completed: {len(self.subscriptions_map)} active subscriptions"
            )

        except Exception as e:
            logger.exception(f"Subscription sync failed: {e}")

    async def periodic_sync_task(self, interval_hours: int = 1) -> None:
        """
        Periodically sync subscriptions with Grist config.

        Args:
            interval_hours: Hours between sync attempts
        """
        while True:
            try:
                await asyncio.sleep(interval_hours * 3600)
                await self.sync_subscriptions()
            except asyncio.CancelledError:
                logger.info("Periodic sync task cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in periodic sync: {e}")
