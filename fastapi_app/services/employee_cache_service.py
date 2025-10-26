import logging
from typing import Optional, Any

from fastapi_app.services.employee import EmployeeService
from fastapi_app.services.redis import RedisService

logger = logging.getLogger(__name__)


class EmployeeCacheService:
    EMPLOYEE_CACHE_TTL = 3600  # 1 hour

    def __init__(self, redis_service: RedisService, employee_service: EmployeeService):
        self.redis_service = redis_service
        self.employee_service = employee_service

    def _get_employee_cache_key(self, telegram_id: str) -> str:
        """Generate cache key for employee"""
        return f'employee:telegram:{telegram_id}'

    async def _get_with_caching(
            self,
            telegram_id: str,
            fetch_func: callable,
            *fetch_args,
            **fetch_kwargs
    ) -> Optional[Any]:
        """Generic method to get data with caching"""
        cache_key = self._get_employee_cache_key(telegram_id)

        # Try cache first
        cached_employee = await self.redis_service.get(cache_key)
        if cached_employee:
            logger.info(f'Cache hit for employee {telegram_id}')
            return cached_employee

        # Cache miss - get from service
        logger.info(f'Cache miss for employee {telegram_id}')
        employee = await fetch_func(*fetch_args, **fetch_kwargs)

        # Cache the result
        if employee:
            await self.redis_service.set(
                cache_key,
                employee,
                expire_seconds=self.EMPLOYEE_CACHE_TTL
            )
            logger.info(f'Cached employee {telegram_id}')

        return employee

    async def get_or_create_employee(
            self,
            *,
            telegram_id: str,
            name: str
    ) -> Optional[Any]:
        """Get or create employee with caching"""
        return await self._get_with_caching(
            telegram_id,
            self.employee_service.get_or_create_employee,
            telegram_id=telegram_id,
            name=name
        )

    async def get_employee_by_telegram_id(
            self,
            *,
            telegram_id: str
    ) -> Optional[Any]:
        """Get employee by telegram ID with caching"""
        return await self._get_with_caching(
            telegram_id,
            self.employee_service.get_employee_by_telegram_id,
            telegram_id=telegram_id
        )

    async def update_employee_email(
            self,
            *,
            telegram_id: str,
            email: str
    ) -> Optional[Any]:
        """Update employee email and refresh cache"""
        # Update in database
        updated_employee = await self.employee_service.update_employee_email(
            telegram_id=telegram_id,
            email=email
        )

        if updated_employee:
            # Refresh cache with updated data
            cache_key = self._get_employee_cache_key(telegram_id)
            await self.redis_service.set(
                cache_key,
                updated_employee,
                expire_seconds=self.EMPLOYEE_CACHE_TTL
            )
            logger.info(f'Refreshed cache for updated employee {telegram_id}')
        else:
            # If update failed, invalidate cache
            await self._invalidate_cache(telegram_id)

        return updated_employee

    async def _invalidate_cache(self, telegram_id: str) -> bool:
        """Invalidate cache for specific employee"""
        cache_key = self._get_employee_cache_key(telegram_id)
        success = await self.redis_service.delete(cache_key)
        if success:
            logger.info(f'Invalidated cache for employee {telegram_id}')
        return success

    # Optional: Keep this if you need explicit cache invalidation
    async def invalidate_employee_cache(self, telegram_id: str) -> bool:
        """Public method to invalidate cache for specific employee"""
        return await self._invalidate_cache(telegram_id)
