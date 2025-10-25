from django.db import models


class Employee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True)
    telegram_id = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class WorkHours(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    regular_hours = models.FloatField(default=0)
    overtime_hours = models.FloatField(default=0)
    vacation_hours = models.FloatField(default=0)
    sick_hours = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Work hours"
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "date"], name="workhours_unique_employee_date"
            )
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.date}"
