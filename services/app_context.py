from services.external_services import (GristService, GSpreadService, WebService, MtlService, 
                                       StellarService, AirdropService, ReportService, AntispamService,
                                       PollService, ModerationService, AIService, TalkService,
                                       GroupService, UtilsService, ConfigService)

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
        self.config_service = None

    @classmethod
    def from_bot_session(cls, bot):
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
        ctx.config_service = ConfigService()
        return ctx
