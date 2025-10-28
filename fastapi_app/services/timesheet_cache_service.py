import logging
import shutil
import tempfile

from openpyxl import load_workbook

from fastapi_app.services.redis import RedisService
from processors.excel_generator import TimeSheetGenerator

logger = logging.getLogger(__name__)


class TimesheetCacheService:
    TIMESHEET_CACHE_TTL = 86400  # 24 hours

    def __init__(self, redis_service: RedisService, timesheet_generator: TimeSheetGenerator):
        self.redis_service = redis_service
        self.timesheet_generator = timesheet_generator
        self.month = self.timesheet_generator.month
        self.year = self.timesheet_generator.year

    def _get_template_cache_key(self, month: int, year: int) -> str:
        return f'timesheet:template:{month:02}:{year}'

    async def generate_timesheet(self, employee_name: str) -> str:
        """Generate a timesheet using cached template"""
        template_cache_key = self._get_template_cache_key(self.month, self.year)

        # Check cache first
        cached_file_path = await self.redis_service.get(template_cache_key)

        if cached_file_path:
            logger.info(f"Cache hit for timesheet {self.month}-{self.year}")
            return await self._generate_timesheet_for_employee_from_template(
                employee_name=employee_name,
                template_path=cached_file_path
            )

        # Cache miss - generate the timesheet
        logger.info(f"Cache miss for timesheet {self.month}/{self.year}")
        template_path = await self.timesheet_generator.generate_timesheet()

        # Cache the template path
        await self.redis_service.set(
            key=template_cache_key,
            value=template_path,
            expire_seconds=self.TIMESHEET_CACHE_TTL
        )
        return await self._generate_timesheet_for_employee_from_template(
            employee_name=employee_name,
            template_path=template_path
        )

    async def _generate_timesheet_for_employee_from_template(self, *, employee_name: str, template_path: str) -> str:
        """Generate employee-specific timesheet from template"""
        try:
            prefix_args = ['Timesheet', employee_name.replace(' ', '_'), f'{self.month:02}', str(self.year)]

            with tempfile.NamedTemporaryFile(
                    prefix='_'.join(prefix_args),
                    suffix='.xlsx',
                    delete=False
            ) as tmp_file:
                employee_file_path = tmp_file.name

                # Copy template to new location
                shutil.copy2(template_path, employee_file_path)

                # Load WB and add employee's name
                workbook = load_workbook(filename=employee_file_path)
                worksheet = workbook.active
                worksheet['A1'].value = employee_name
                workbook.save(filename=employee_file_path)
                workbook.close()
                logger.info(f'✅ Generated timesheet from template for {employee_name}: {employee_file_path}')
                return employee_file_path

        except Exception as e:
            logger.error(f'❌ Error generating from template for {employee_name}: {str(e)}')
            return await self.timesheet_generator.generate_timesheet(employee_name=employee_name)

    async def invalidate_all_timesheets(self):
        """Invalidate all cached timesheets"""
        pattern = "timesheet:*"
        await self.redis_service.delete_pattern(pattern)
        logger.info("Invalidated all cached timesheets")
