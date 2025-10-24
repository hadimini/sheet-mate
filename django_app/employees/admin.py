from django.contrib import admin

from django_app.employees.models import Employee, WorkHours


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(WorkHours)
class WorkHoursAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'regular_hours', 'overtime_hours', 'vacation_hours']
    list_filter = ['date']
    search_fields = ['employee__name']
    date_hierarchy = 'date'
