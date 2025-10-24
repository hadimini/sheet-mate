import calendar
import os
import tempfile
from datetime import datetime, timedelta

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


class TimeSheetGenerator:
    def __init__(self) -> None:
        self.current_date = datetime.now()
        self.month = self.current_date.month
        self.year = self.current_date.year

    def _apply_styling(self, ws) -> None:
        """Apply styling to worksheet"""
        # Set columns width
        for col in range(1, 50):
            ws.column_dimensions[chr(64 + col)].width = 10

        # Base border
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Apply borders to data area
        for row in range(1, 20):
            for col in range(1, 40):
                cell = ws.cell(row=row, column=col)
                cell.border = thin_border

    def _build_timesheet_structure(self, ws, employee_name: str, calendar_data: dict) -> None:
        """Build timesheet structure"""
        # Title
        ws.merge_cells('A1:H1')
        ws['A1'] = f'Employee Timesheet - {calendar_data["month_name"]} {calendar_data["year"]}'
        ws['A1'].font = Font(size=14, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')

        # Employee info
        ws['A3'] = 'Employee:'
        ws['B3'] = employee_name
        ws['A4'] = 'Employee ID:'
        ws['B4'] = 'employee_id'
        ws['A5'] = 'Period:'
        ws['B5'] = f'{calendar_data["month_name"]} {calendar_data["year"]}'

    def _generate_calendar_data(self) -> dict:
        """Generates calendar data from first day of the month"""
        month_name = calendar.month_name[self.month]
        first_day = datetime(self.year, self.month, 1)
        total_days = calendar.monthrange(self.year, self.month)[1]

        days_in_month = []
        day_details = []
        weeks = []
        current_week = []

        for day in range(1, total_days + 1):
            current_date = datetime(self.year, self.month, day)
            dya_of_week = current_date.weekday()
            is_weekend = dya_of_week >= 5

            days_in_month.append(day)
            day_details.append({
                'day': current_date,
                'date_of_week': dya_of_week,
                'is_weekend': is_weekend,
            })

            current_week.append(day)

            if dya_of_week == 6 or day == total_days:
                weeks.append(current_week)
                current_week = []

        if current_week:
            weeks.append(current_week)

        return {
            'month_name': month_name,
            'year': self.year,
            'days': days_in_month,
            'day_details': day_details,
            'weeks': weeks,
        }

    async def generate_timesheet(self, employee_name: str) -> str:
        """Generates a timesheet Excel file"""
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f'Timesheet {self.month}-{self.year}'

        # Calendar data
        calendar_data: dict = self._generate_calendar_data()

        # Build structure
        self._build_timesheet_structure(ws, employee_name, calendar_data)

        # Apply styling
        self._apply_styling(ws)

        # Save to temp file
        file_path = f"/tmp/{employee_name}_{self.month}_{self.year}.xlsx"
        wb.save(file_path)

        return file_path
