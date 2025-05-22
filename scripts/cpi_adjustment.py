from Payroll_app.models import Employee

def adjust_salaries_by_cpi(cpi_rate):
    employees = Employee.objects.all()
    for emp in employees:
        emp.salary *= (1 + cpi_rate)
        emp.save()
    print(f"Adjusted {len(employees)} salaries by CPI rate {cpi_rate}")