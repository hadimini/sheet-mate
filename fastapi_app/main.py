import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from bot.telegram_bot import TelegramBot
from fastapi_app.services.redis import RedisService

logger = logging.getLogger(__name__)

# Initialize bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL', None)
REDIS_URL = os.getenv('REDIS_URL', None)
WEBHOOK_PATH = '/webhook/telegram'

bot = None
redis_service = RedisService(redis_url=REDIS_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info('Starting Sheet Mate API')

    # Initialize Redis connection
    try:
        await redis_service.connect()
        logger.info('Connected to Redis')
    except Exception as e:
        logger.error(f'Failed to connect to Redis: {e}')

    # Initialize Telegram bot
    global bot
    bot = TelegramBot(
        token=TELEGRAM_BOT_TOKEN, webhook_url=f'{API_BASE_URL}{WEBHOOK_PATH}', redis_service=redis_service
    )

    try:
        await bot.setup_webhook()
        logger.info('Bot webhook configured successfully')
    except Exception as e:
        logger.error(f'Failed to setup webhook: {e}')

    yield

    # Shutdown
    logger.info('Shutting down Sheet Mate API')

    try:
        await redis_service.disconnect()
        logger.info('Redis disconnected successfully')
    except Exception as e:
        logger.error(f'Error disconnecting Redis: {e}')

    if bot:
        await bot.remove_webhook()
        logger.info('Bot webhook removed successfully')

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

# Dependency for Redis service
def get_redis_service():
    return redis_service

@app.get('/')
async def root():
    return {'message': 'Sheet Mate API', 'status': 'running'}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates"""
    if not bot:
        raise HTTPException(status_code=503, detail='Bot not initialized')

    try:
        update_data = await request.json()
        await bot.process_update(update_data)
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f'Error processing webhook: {e}')
        raise HTTPException(status_code=500, detail='Error processing webhook')


@app.get('/health')
async def health_check(redis_service: RedisService = Depends(get_redis_service)):
    bot_status = 'initialized' if bot else 'not initialized'

    # Check Redis health
    redis_status = 'unknown'
    try:
        if redis_service.client:
            await redis_service.client.ping()
            redis_status = 'connected'
        else:
            redis_status = 'not connected'
    except Exception as e:
        redis_status = f'error: {e}'

    return {
        'status': 'healthy',
        'bot': bot_status,
        'redis': redis_status,
        'webhook_url': f'{API_BASE_URL}{WEBHOOK_PATH}' if API_BASE_URL else 'not set'
    }
