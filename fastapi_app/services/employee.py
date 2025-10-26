import logging
import re
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from fastapi_app.database import AsyncSessionLocal
from fastapi_app.tables import employees as employees_table

logger = logging.getLogger(__name__)


class EmployeeService:

    async def get_or_create_employee(self, *, telegram_id: str, name: str):
        """Get existing employee by telegram id or create new one"""
        async with AsyncSessionLocal() as db:
            try:
                employee = await self.get_employee_by_telegram_id(telegram_id=telegram_id)

                if employee:
                    return employee

                # Create new employee
                insert_stmt = employees_table.insert().values(
                    name=name,
                    telegram_id=telegram_id,
                    email=None,
                    is_active=True,
                    created_at=datetime.now(),
                )
                await db.execute(insert_stmt)
                await db.commit()

                new_employee = await self.get_employee_by_telegram_id(telegram_id=telegram_id)
                return new_employee

            except Exception as e:
                await db.rollback()
                logger.error(f'Error in get_or_create_employee: {e}')
                raise

    async def update_employee_email(self, *, telegram_id: str, email: str):
        """Update employee email with validation"""
        async with AsyncSessionLocal() as db:
            try:
                # Validate email format
                if not self._is_valid_email(email):
                    raise ValueError('Invalid email format')

                # Check if employee exists
                stmt = select(employees_table).where(employees_table.c.telegram_id == telegram_id)
                result = await db.execute(stmt)
                employee = result.fetchone()

                if not employee:
                    raise ValueError('Employee not found')

                # Update email
                update_stmt = (
                    employees_table.update()
                    .where(employees_table.c.telegram_id == telegram_id)
                    .values(email=email)
                )
                await db.execute(update_stmt)
                await db.commit()

                # **FIX: Re-query to get updated employee**
                stmt = select(employees_table).where(employees_table.c.telegram_id == telegram_id)
                result = await db.execute(stmt)
                return result.fetchone()
            except IntegrityError:
                await db.rollback()
                logger.error(f'Email already exists: {email}')
                raise ValueError('Email already registered')
            except ValueError as e:
                await db.rollback()
                logger.error(f'Validation error in update_employee_email: {e}')
                raise
            except Exception as e:
                await db.rollback()
                logger.error(f'Error in update_employee_email: {e}')
                raise

    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    async def get_employee_by_telegram_id(self, *, telegram_id: str):
        '''Get employee by telegram ID'''
        async with AsyncSessionLocal() as db:
            try:
                stmt = select(employees_table).where(employees_table.c.telegram_id == telegram_id)
                result = await db.execute(stmt)
                return result.fetchone()
            except Exception as e:
                logger.error(f'Error in get_employee_by_telegram_id: {e}')
                raise
