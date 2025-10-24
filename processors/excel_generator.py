import calendar
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import tempfile


class TimeSheetGenerator:
    def __init__(self) -> None:
        self.current_date = datetime.now()
        self.month = self.current_date.month
        self.year = self.current_date.year

    async def generate_timesheet(self, employee_name: str) -> str:
        """Generates a clean, simple timesheet Excel file"""
        try:
            print(f"📊 Generating timesheet for {employee_name}...")

            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = 'Timesheet'

            # SIMPLE HEADER
            ws['A1'] = f"Timesheet - {employee_name}"
            ws['A1'].font = Font(size=14, bold=True)

            ws['A2'] = f"Period: {calendar.month_name[self.month]} {self.year}"
            ws['A2'].font = Font(bold=True)

            # SIMPLE TABLE HEADERS
            headers = ['Date', 'Day', 'Regular Hours', 'Overtime Hours', 'Total Hours']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col, value=header)
                cell.font = Font(bold=True)

            # FILL DATES FOR THE MONTH
            total_days = calendar.monthrange(self.year, self.month)[1]
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

            current_row = 5
            for day in range(1, total_days + 1):
                current_date = datetime(self.year, self.month, day)
                day_name = day_names[current_date.weekday()]
                is_weekend = current_date.weekday() >= 5

                # Date
                ws.cell(row=current_row, column=1, value=current_date.strftime('%Y-%m-%d'))

                # Day name
                ws.cell(row=current_row, column=2, value=day_name)

                # Sample hours (8 for weekdays, 0 for weekends)
                regular_hours = 0 if is_weekend else 8
                ws.cell(row=current_row, column=3, value=regular_hours)

                # Overtime (sample: 1 hour on Fridays)
                overtime_hours = 1 if current_date.weekday() == 4 else 0  # Friday
                ws.cell(row=current_row, column=4, value=overtime_hours)

                # Total
                ws.cell(row=current_row, column=5, value=regular_hours + overtime_hours)

                current_row += 1

            # AUTO-ADJUST COLUMN WIDTHS
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column_letter].width = adjusted_width

            # SAVE FILE
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                file_path = tmp_file.name

            wb.save(file_path)
            print(f"✅ Timesheet saved: {file_path}")

            return file_path

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            print(f"🔍 Details: {traceback.format_exc()}")
            raise