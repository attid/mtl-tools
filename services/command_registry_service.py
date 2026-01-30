"""Command registry service with DI."""

from typing import Callable, Optional
from threading import Lock
from dataclasses import dataclass, field


# Module-level storage for decorator registrations
_pending_commands: dict[str, dict] = {}


def update_command_info(command_name: str, info: str, cmd_type: int = 0, cmd_list: str = ''):
    """Decorator to register command info at module load time.

    Args:
        command_name: The command name (e.g., 'help', 'start')
        info: Description of what the command does
        cmd_type: Command type (0=none, 1=in list, 2=in dict, 3=dict with users)
        cmd_list: Command list identifier
    """
    def decorator(func: Callable) -> Callable:
        _pending_commands[command_name] = {
            'info': info,
            'cmd_type': cmd_type,
            'cmd_list': cmd_list
        }
        return func
    return decorator


def get_pending_commands() -> dict[str, dict]:
    """Get all commands registered via decorators."""
    return _pending_commands.copy()


@dataclass
class CommandInfo:
    """Command metadata for help system."""
    name: str
    description: str = ""
    cmd_type: int = 0  # 0=none, 1=in list, 2=in dict, 3=dict with users
    cmd_list: list[str] = field(default_factory=list)
    hidden: bool = False


class CommandRegistryService:
    """
    Service for command registration and help system.

    Replaces global_data.info_cmd attribute.
    """

    def __init__(self):
        self._lock = Lock()
        self._commands: dict[str, CommandInfo] = {}

    def register_command(
        self,
        name: str,
        description: str = "",
        cmd_type: int = 0,
        cmd_list: Optional[list[str]] = None,
        hidden: bool = False,
    ) -> None:
        """Register a command with metadata."""
        with self._lock:
            self._commands[name] = CommandInfo(
                name=name,
                description=description,
                cmd_type=cmd_type,
                cmd_list=cmd_list or [],
                hidden=hidden,
            )

    def get_command(self, name: str) -> Optional[CommandInfo]:
        """Get command info by name."""
        with self._lock:
            return self._commands.get(name)

    def get_all_commands(self) -> dict[str, CommandInfo]:
        """Get all registered commands."""
        with self._lock:
            return self._commands.copy()

    def get_commands_by_type(self, cmd_type: int) -> list[CommandInfo]:
        """Get commands filtered by type."""
        with self._lock:
            return [
                cmd for cmd in self._commands.values()
                if cmd.cmd_type == cmd_type and not cmd.hidden
            ]

    def get_visible_commands(self) -> list[CommandInfo]:
        """Get all non-hidden commands."""
        with self._lock:
            return [cmd for cmd in self._commands.values() if not cmd.hidden]

    def unregister_command(self, name: str) -> bool:
        """Unregister a command. Returns True if existed."""
        with self._lock:
            if name in self._commands:
                del self._commands[name]
                return True
            return False

    def has_command(self, name: str) -> bool:
        """Check if command is registered."""
        with self._lock:
            return name in self._commands

    def update_command(self, name: str, **kwargs) -> bool:
        """Update existing command fields. Returns True if command exists."""
        with self._lock:
            if name not in self._commands:
                return False
            cmd = self._commands[name]
            for key, value in kwargs.items():
                if hasattr(cmd, key):
                    setattr(cmd, key, value)
            return True

    # Bulk loading for initialization
    def load_commands(self, commands_data: dict[str, dict]) -> None:
        """Bulk load commands from dict.

        Supports both new format (description, cmd_list as list) and
        legacy format from global_data.info_cmd (info, cmd_list as string).
        """
        with self._lock:
            self._commands = {}
            for name, data in commands_data.items():
                # Support both 'description' and legacy 'info' key
                description = data.get('description') or data.get('info', '')
                # Support cmd_list as string (legacy) or list (new)
                cmd_list = data.get('cmd_list', [])
                if isinstance(cmd_list, str):
                    cmd_list = [cmd_list] if cmd_list else []

                self._commands[name] = CommandInfo(
                    name=name,
                    description=description,
                    cmd_type=data.get('cmd_type', 0),
                    cmd_list=cmd_list,
                    hidden=data.get('hidden', False),
                )
