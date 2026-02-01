"""Health check HTTP server for Docker healthcheck."""

from datetime import datetime

from aiohttp import web
from loguru import logger

from services.bot_state_service import BotStateService

HEALTH_TIMEOUT = 180  # 3 minutes


async def health_handler(request: web.Request) -> web.Response:
    bot_state: BotStateService = request.app["bot_state"]
    last_ping = bot_state.get_last_ping_sent()

    if last_ping is None:
        # Bot just started, no ping sent yet
        return web.json_response({"status": "starting"}, status=200)

    age = (datetime.now() - last_ping).total_seconds()
    if age > HEALTH_TIMEOUT:
        return web.json_response(
            {"status": "unhealthy", "last_ping_age": age},
            status=503,
        )

    return web.json_response({"status": "healthy", "last_ping_age": age})


async def start_health_server(
    bot_state: BotStateService, port: int = 8080
) -> web.AppRunner:
    app = web.Application()
    app["bot_state"] = bot_state
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server started on port {port}")
    return runner
