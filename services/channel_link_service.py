"""Service for managing channel-to-user links.

When admins send commands from a channel (sender_chat), the bot needs to know
which user owns the channel to properly attribute the command.
"""


class ChannelLinkService:
    """Manages channel-to-user ID mappings."""

    def __init__(self):
        self._channel_to_user: dict[int, dict[str, int | str | None] | int] = {}

    def get_user_for_channel(self, channel_id: int) -> int | None:
        """Get the user ID linked to a channel.

        Args:
            channel_id: The channel ID to look up.

        Returns:
            The user ID if the channel is linked, None otherwise.
        """
        value = self._channel_to_user.get(channel_id)
        if isinstance(value, dict):
            user_id = value.get("user_id")
            return int(user_id) if isinstance(user_id, (int, str)) else None
        return value if isinstance(value, int) else None

    def get_username_for_channel(self, channel_id: int) -> str | None:
        """Get the username linked to a channel (if stored)."""
        value = self._channel_to_user.get(channel_id)
        if isinstance(value, dict):
            username = value.get("username")
            return str(username) if username is not None else None
        return None

    def link_channel(self, channel_id: int, user_id: int, username: str | None = None) -> None:
        """Link a channel to a user.

        Args:
            channel_id: The channel ID to link.
            user_id: The user ID (owner) to link the channel to.
            username: The user username (if available).
        """
        self._channel_to_user[channel_id] = {"user_id": user_id, "username": username}

    def unlink_channel(self, channel_id: int) -> bool:
        """Unlink a channel.

        Args:
            channel_id: The channel ID to unlink.

        Returns:
            True if the channel was linked and is now unlinked, False if it wasn't linked.
        """
        if channel_id in self._channel_to_user:
            del self._channel_to_user[channel_id]
            return True
        return False

    def is_linked(self, channel_id: int) -> bool:
        """Check if a channel is linked to any user.

        Args:
            channel_id: The channel ID to check.

        Returns:
            True if the channel is linked, False otherwise.
        """
        return channel_id in self._channel_to_user

    def get_all_links(self) -> dict[int, dict[str, int | str | None] | int]:
        """Get all channel-to-user links.

        Returns:
            A copy of the channel-to-user mapping.
        """
        return self._channel_to_user.copy()

    def load_from_dict(self, data: dict[str, int]) -> None:
        """Load channel links from a dictionary (typically from JSON storage).

        Args:
            data: Dictionary mapping channel_id (as string) to user_id.
        """
        self._channel_to_user = {}
        for key, value in data.items():
            channel_id = int(key)
            if isinstance(value, dict):
                user_id = value.get("user_id")
                if isinstance(user_id, str) and user_id.isdigit():
                    user_id = int(user_id)
                username = value.get("username")
                self._channel_to_user[channel_id] = {"user_id": user_id, "username": username}
            else:
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                self._channel_to_user[channel_id] = value
