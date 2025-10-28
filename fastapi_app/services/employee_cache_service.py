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
            **fetch_kwargs
    ) -> Optional[Any]:
        cache_key = self._get_employee_cache_key(telegram_id)

        # Try cache first
        cached_data = await self.redis_service.get(cache_key)

        if cached_data:
            logger.info(f'Cache hit for employee {telegram_id}')
            return cached_data

        # Cache miss - get from service
        logger.info(f'Cache miss for employee {telegram_id}')
        employee = await fetch_func(telegram_id=telegram_id, **fetch_kwargs)

        # Cache the result
        if employee:
            # Convert Row object to dict for proper caching
            employee_dict = self._row_to_dict(employee)
            await self.redis_service.set(
                key=cache_key,
                value=employee_dict,  # Store as dict instead of Row
                expire_seconds=self.EMPLOYEE_CACHE_TTL
            )
            logger.info(f'Cached employee {telegram_id}')

        return employee  # Return original Row object, not the dict

    def _row_to_dict(self, row):
        """Convert SQLAlchemy Row object to dictionary"""
        if hasattr(row, '_asdict'):
            # Row object with _asdict method
            return row._asdict()
        elif hasattr(row, '_fields'):
            # Namedtuple-like object
            return {field: getattr(row, field) for field in row._fields}
        elif isinstance(row, (tuple, list)):
            # It's a plain tuple - convert to dict with column names
            columns = ['id', 'name', 'email', 'telegram_id', 'is_active', 'created_at']
            return dict(zip(columns, row))
        else:
            return row

    async def get_or_create_employee(
            self,
            telegram_id: str,
            name: str
    ) -> Optional[Any]:
        """Get or create employee with caching"""
        return await self._get_with_caching(
            telegram_id=telegram_id,
            fetch_func=self.employee_service.get_or_create_employee,
            name=name
        )

    async def get_employee_by_telegram_id(
            self,
            telegram_id: str
    ) -> Optional[Any]:
        """Get employee by telegram ID with caching"""
        return await self._get_with_caching(
            telegram_id=telegram_id,
            fetch_func=self.employee_service.get_employee_by_telegram_id,
        )

    async def update_employee_email(
            self,
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
                key=cache_key,
                value=updated_employee,
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

    async def invalidate_employee_cache(self, telegram_id: str) -> bool:
        """Public method to invalidate cache for specific employee"""
        return await self._invalidate_cache(telegram_id)
