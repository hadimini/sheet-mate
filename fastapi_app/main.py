import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bot.telegram_bot import TelegramBot
from fastapi_app.routes import router

logger = logging.getLogger(__name__)
telegram_bot = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Starting Sheet Mate API')

    if bot_token := os.getenv('TELEGRAM_BOT_TOKEN'):
        global telegram_bot

        telegram_bot = TelegramBot(bot_token)
        asyncio.create_task(telegram_bot.start_polling())
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set - bot functionality disabled")

    yield

    logger.info('Shutting down Sheet Mate API')

    if telegram_bot:
        await telegram_bot.application.stop()
        logger.info('Telegram Bot stopped')

app = FastAPI(
    title='Sheet Mate API',
    description='Excel timesheet processing and Telegram bot',
    version='1.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
