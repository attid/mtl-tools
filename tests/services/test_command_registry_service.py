"""Tests for CommandRegistryService."""

from services.command_registry_service import CommandRegistryService, CommandInfo


class TestCommandRegistryServiceBasicOperations:
    """Tests for basic command registration and retrieval."""

    def test_register_and_get_command(self):
        service = CommandRegistryService()
        service.register_command(
            name="help",
            description="Show help",
            cmd_type="user",
            cmd_list=["help", "h"],
        )
        result = service.get_command("help")
        assert result is not None
        assert result.name == "help"
        assert result.description == "Show help"
        assert result.cmd_type == "user"
        assert result.cmd_list == ["help", "h"]
        assert result.hidden is False

    def test_get_nonexistent_command_returns_none(self):
        service = CommandRegistryService()
        result = service.get_command("nonexistent")
        assert result is None

    def test_has_command_returns_true_for_existing(self):
        service = CommandRegistryService()
        service.register_command(name="test")
        assert service.has_command("test") is True

    def test_has_command_returns_false_for_nonexistent(self):
        service = CommandRegistryService()
        assert service.has_command("nonexistent") is False

    def test_register_command_with_defaults(self):
        service = CommandRegistryService()
        service.register_command(name="simple")
        result = service.get_command("simple")
        assert result is not None
        assert result.name == "simple"
        assert result.description == ""
        assert result.cmd_type == 0
        assert result.cmd_list == []
        assert result.hidden is False


class TestCommandRegistryServiceUnregister:
    """Tests for command unregistration."""

    def test_unregister_existing_command(self):
        service = CommandRegistryService()
        service.register_command(name="test")
        result = service.unregister_command("test")
        assert result is True
        assert service.has_command("test") is False

    def test_unregister_nonexistent_command(self):
        service = CommandRegistryService()
        result = service.unregister_command("nonexistent")
        assert result is False


class TestCommandRegistryServiceUpdate:
    """Tests for command updates."""

    def test_update_existing_command(self):
        service = CommandRegistryService()
        service.register_command(name="test", description="Old description")
        result = service.update_command("test", description="New description")
        assert result is True
        cmd = service.get_command("test")
        assert cmd.description == "New description"

    def test_update_nonexistent_command(self):
        service = CommandRegistryService()
        result = service.update_command("nonexistent", description="New")
        assert result is False

    def test_update_multiple_fields(self):
        service = CommandRegistryService()
        service.register_command(name="test")
        service.update_command("test", description="Updated", hidden=True)
        cmd = service.get_command("test")
        assert cmd.description == "Updated"
        assert cmd.hidden is True


class TestCommandRegistryServiceQueries:
    """Tests for querying commands."""

    def test_get_all_commands(self):
        service = CommandRegistryService()
        service.register_command(name="cmd1")
        service.register_command(name="cmd2")
        result = service.get_all_commands()
        assert len(result) == 2
        assert "cmd1" in result
        assert "cmd2" in result

    def test_get_all_commands_returns_copy(self):
        service = CommandRegistryService()
        service.register_command(name="cmd1")
        result = service.get_all_commands()
        result["cmd2"] = CommandInfo(name="cmd2")
        assert "cmd2" not in service.get_all_commands()

    def test_get_commands_by_type(self):
        service = CommandRegistryService()
        service.register_command(name="admin1", cmd_type="admin")
        service.register_command(name="admin2", cmd_type="admin")
        service.register_command(name="user1", cmd_type="user")
        result = service.get_commands_by_type("admin")
        assert len(result) == 2
        assert all(cmd.cmd_type == "admin" for cmd in result)

    def test_get_commands_by_type_excludes_hidden(self):
        service = CommandRegistryService()
        service.register_command(name="visible", cmd_type="admin")
        service.register_command(name="hidden", cmd_type="admin", hidden=True)
        result = service.get_commands_by_type("admin")
        assert len(result) == 1
        assert result[0].name == "visible"

    def test_get_visible_commands(self):
        service = CommandRegistryService()
        service.register_command(name="visible1")
        service.register_command(name="visible2")
        service.register_command(name="hidden1", hidden=True)
        result = service.get_visible_commands()
        assert len(result) == 2
        assert all(not cmd.hidden for cmd in result)


class TestCommandRegistryServiceBulkLoad:
    """Tests for bulk loading commands."""

    def test_load_commands(self):
        service = CommandRegistryService()
        commands_data = {
            "help": {
                "description": "Show help",
                "cmd_type": "user",
                "cmd_list": ["help", "h"],
            },
            "admin": {
                "description": "Admin panel",
                "cmd_type": "admin",
                "hidden": True,
            },
        }
        service.load_commands(commands_data)
        assert service.has_command("help")
        assert service.has_command("admin")
        help_cmd = service.get_command("help")
        assert help_cmd.description == "Show help"
        assert help_cmd.cmd_list == ["help", "h"]
        admin_cmd = service.get_command("admin")
        assert admin_cmd.hidden is True

    def test_load_commands_clears_existing(self):
        service = CommandRegistryService()
        service.register_command(name="old")
        service.load_commands({"new": {"description": "New command"}})
        assert not service.has_command("old")
        assert service.has_command("new")
