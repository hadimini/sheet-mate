from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def root():
    return {'message': 'Sheet Mate API', 'status': 'running'}


@router.post('/telegram')
async def telegram_webhook():
    return {'status': 'running'}
