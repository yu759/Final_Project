import calendar
from django.utils import timezone
from Payroll_app.models import Payroll, Employee
from django.db.models import Sum

def get_dashboard_stats():
    now = timezone.now()  # Get the current date and time
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)  # Get the start of the current month
    end_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1], hour=23, minute=59, second=59,
                               microsecond=999)  # Get the end of the current month

    payrolls = Payroll.objects.filter(
        pay_date__range=(start_of_month, end_of_month)  # Filter for payrolls within the current month
    )
    employees = Employee.objects.all()

    total_payroll = sum(
        (p.employee.salary or 0) + (p.bonus or 0) +
        sum(a.amount for a in p.employee.allowances.all()) -
        sum(d.amount for d in p.employee.deductions.all())
        for p in payrolls
    )
    net_salaries = [
        (p.employee.salary or 0) + (p.bonus or 0) +
        sum(a.amount for a in p.employee.allowances.all()) -
        sum(d.amount for d in p.employee.deductions.all())
        for p in payrolls
    ]
    avg_net_salary = sum(net_salaries) / len(net_salaries) if net_salaries else 0
    total_bonuses = payrolls.aggregate(bonus=Sum('bonus'))['bonus'] or 0

    return {
        'total_payroll': f"{total_payroll:.2f}",
        'avg_net_salary': f"{avg_net_salary:.2f}",
        'total_bonuses': f"{total_bonuses:.2f}",
        'employee_count': employees.count(),
        'active_employees': employees.filter(is_active=True).count(),
        'pending_adjustments': 0,
        'overdue_reports': 0
    }
