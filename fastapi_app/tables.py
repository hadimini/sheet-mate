from sqlalchemy import Table, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, MetaData, String

metadata = MetaData()

employees = Table(
    'employees_employee',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(100)),
    Column('email', String(254), unique=True),
    Column('telegram_id', String(50), unique=True),
    Column('is_active', Boolean),
    Column('created_at', DateTime),
)

workhours = Table(
    'employees_workhours',
    metadata,
    Column('id', Integer, primary_key=True),

    Column('employee_id', Integer, ForeignKey('employees_employee.id')),
    Column('date', Date),
    Column('regular_hours', Float, default=0),
    Column('overtime_hours', Float, default=0),
    Column('vacation_hours', Float, default=0),
    Column('sick_hours', Float, default=0),
    Column('created_at', DateTime),
)
