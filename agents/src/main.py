import asyncio
import logging

import uvicorn

from .config import settings
from .db import init_db
from .interfaces.telegram_bot import run_bot
from .interfaces.web import app as web_app
from .orchestrator import worker_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
log = logging.getLogger("main")


async def run_web() -> None:
    config = uvicorn.Config(
        web_app, host=settings.web_host, port=settings.web_port,
        log_level="info", access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    init_db()
    log.info("starting orchestrator + telegram + web")
    await asyncio.gather(
        worker_loop(),
        run_bot(),
        run_web(),
    )


if __name__ == "__main__":
    asyncio.run(main())
