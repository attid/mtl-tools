from services.external_services import (GristService, GSpreadService, WebService, MtlService,
                                       StellarService, AirdropService, ReportService, AntispamService,
                                       PollService, ModerationService, AIService, TalkService,
                                       GroupService, UtilsService, ConfigService as LegacyConfigService)
from services.user_service import UserService
from services.config_service import ConfigService
from services.feature_flags import FeatureFlagsService
from services.notification_service import NotificationService
from services.bot_state_service import BotStateService
from services.voting_service import VotingService
from services.admin_service import AdminManagementService
from services.command_registry_service import CommandRegistryService


class AppContext:
    def __init__(self):
        self.grist_service = None
        self.gspread_service = None
        self.web_service = None
        self.mtl_service = None
        self.stellar_service = None
        self.airdrop_service = None
        self.report_service = None
        self.antispam_service = None
        self.poll_service = None
        self.moderation_service = None
        self.ai_service = None
        self.talk_service = None
        self.group_service = None
        self.utils_service = None
        self.legacy_config_service = None
        # New DI-based services
        self.user_service = None
        self.config_service = None
        self.feature_flags = None
        self.notification_service = None
        self.bot_state_service = None
        self.voting_service = None
        self.admin_service = None
        self.command_registry = None

    @classmethod
    def from_bot_session(cls, bot, session=None):
        ctx = cls()
        ctx.grist_service = GristService()
        ctx.gspread_service = GSpreadService()
        ctx.web_service = WebService()
        ctx.mtl_service = MtlService()
        ctx.stellar_service = StellarService()
        ctx.airdrop_service = AirdropService()
        ctx.report_service = ReportService()
        ctx.antispam_service = AntispamService()
        ctx.poll_service = PollService()
        ctx.moderation_service = ModerationService()
        ctx.ai_service = AIService()
        ctx.talk_service = TalkService(bot)
        ctx.group_service = GroupService()
        ctx.utils_service = UtilsService()
        ctx.legacy_config_service = LegacyConfigService()

        # Initialize new DI-based services if session provided
        if session:
            from db.repositories import ConfigRepository, ChatsRepository

            config_repo = ConfigRepository(session)
            chats_repo = ChatsRepository(session)

            ctx.config_service = ConfigService(config_repo)
            ctx.user_service = UserService(chats_repo)
            ctx.feature_flags = FeatureFlagsService(ctx.config_service)

        # Services that don't depend on session
        ctx.bot_state_service = BotStateService()
        ctx.voting_service = VotingService()
        ctx.admin_service = AdminManagementService()
        ctx.notification_service = NotificationService()
        ctx.command_registry = CommandRegistryService()

        # Load commands from global_data.info_cmd (filled by @update_command_info decorators)
        from other.global_data import global_data
        if global_data.info_cmd:
            ctx.command_registry.load_commands(global_data.info_cmd)

        return ctx
