import os
from decimal import Decimal
import django
import random
from faker import Faker
from datetime import timedelta
from django.core.management.base import BaseCommand
from Payroll_app.models import *
from Payroll_app import utils

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Final_Project.settings')
django.setup()
User = get_user_model()


class Command(BaseCommand):
    help = "Generate fake data for testing"

    def handle(self, *args, **kwargs):
        global GENERATING_DATA
        utils.GENERATING_DATA = True
        fake = Faker('en_GB')
        # Disconnect the signal connection
        #post_save.disconnect(receiver=create_user_for_employee, sender=Employee)



        # A list of positions related to finance
        financial_positions = [
            "Financial Analyst",
            "Accountant",
            "Investment Banker",
            "Portfolio Manager",
            "Risk Manager",
            "Compliance Officer",
            "Auditor",
            "Trader",
            "Actuary",
            "Financial Planner",
            "Loan Officer",
            "Branch Manager",
            "Customer Service Representative",
            "Operations Analyst",
            "Settlement Clerk"
        ]

        # A list of department names related to finance
        financial_departments = [
            "Accounting",
            "Finance",
            "Investment Banking",
            "Wealth Management",
            "Risk Management",
            "Compliance",
            "Audit",
            "Trading",
            "Actuarial",
            "Retail Banking",
            "Commercial Lending",
            "Operations",
            "Human Resources",
            "Information Technology",
            "Legal"
        ]

        def create_departments(n=10):
            departments = []
            for _ in range(n):
                dept_name = random.choice(financial_departments)
                budget = Decimal(f"{random.uniform(100000, 1000000):.2f}")
                department, created=Department.objects.get_or_create(
                    dept_name=dept_name[:100],
                    defaults={'budget': budget}
                )
                departments.append(department)
            return departments

        def create_positions(n=15):
            positions = []
            for _ in range(n):
                title = random.choice(financial_positions)
                permissions = {"view": True, "edit": random.choice([True, False])}
                positions.append(Position.objects.create(title=title[:100], permissions=permissions))
            return positions

        def create_users(n=50):
            users = []
            for _ in range(n):
                email = fake.unique.email()
                password = 'test1234'
                role = random.choice(['admin', 'user'])
                user = CustomUser.objects.create_user(email=email, password=password, role=role)
                users.append(user)
            return users

        def create_employees(users, departments, positions):
            employees = []
            print(f"Number of users to process: {len(users)}")  # testing
            for user in users:
                #Check whether it is bound
                if not hasattr(user, 'employee'):
                    print(f"Creating employee for user: {user.email}")  # testing
                    hire_date = fake.date_between(start_date='-5y', end_date='today')
                    exit_date = hire_date + timedelta(days=random.randint(200, 1000)) if random.random() < 0.2 else None
                    first_name = fake.first_name()[:50]
                    last_name = fake.last_name()[:50]
                    emp = Employee.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        email=user.email,
                        phone=fake.phone_number()[:20],
                        hire_date=hire_date,
                        exit_date=exit_date,
                        salary=Decimal(f"{random.uniform(40000, 250000):.2f}"),
                        department=random.choice(departments),
                        position=random.choice(positions),
                        rank=random.choice(['Analyst', 'Associate', 'VP', 'Director']),
                        grade=random.choice(['A', 'B', 'C', 'D']),
                    )
                    # create password and save
                    password = emp.generate_password()
                    print(f"User: {user.email}, Password: {password}")  # Print plaintext password
                    with open('new_user_passwords.txt', 'a') as f:
                        f.write(f"{user.email}\t{password}\n")
                    user.set_password(password)
                    user.save()
                    employees.append(emp)
                else:
                    print(f"Employee already exists for user: {user.email}")  # testing
            print(f"Number of employees created: {len(employees)}")  # testing
            return employees

        def create_bonuses(employees):
            if not employees:  # # Add a check. It will not be executed if the employees list is empty
                self.stdout.write(self.style.WARNING("Employee list is empty, skipping bonus creation."))
                return
            for _ in range(50):
                Bonus.objects.create(
                    amount=Decimal(f"{random.uniform(1000, 20000):.2f}"),
                    bonus_type=random.choice(['Performance Bonus', 'Year-End Bonus', 'Deal Bonus', 'Sign-on Bonus'])[:50],
                    date_awarded=fake.date_between(start_date='-1y', end_date='today'),
                    employee=random.choice(employees)
                )

        def create_allowances(employees):
            if not employees:
                self.stdout.write(self.style.WARNING("Employee list is empty, skipping allowance creation."))
                return
            allowance_types = ['Transportation Allowance', 'Meal Allowance', 'Housing Allowance', 'Professional Development Allowance']
            for _ in range(50):
                Allowance.objects.create(
                    employee=random.choice(employees),
                    allowance_type=random.choice(allowance_types)[:50],
                    amount=Decimal(f"{random.uniform(200, 2000):.2f}"),
                    effective_date=fake.date_between(start_date='-2y', end_date='today')
                )

        def create_deductions(employees):
            if not employees:
                self.stdout.write(self.style.WARNING("Employee list is empty, skipping deduction creation."))
                return
            deduction_types = ['Income Tax', 'National Insurance', 'Pension Contribution', 'Health Insurance', 'Professional Membership Fees']
            for _ in range(50):
                Deduction.objects.create(
                    employee=random.choice(employees),
                    deduction_type=random.choice(deduction_types)[:50],
                    amount=Decimal(f"{random.uniform(100, 1500):.2f}"),
                    effective_date=fake.date_between(start_date='-2y', end_date='today')
                )

        def create_taxes(employees):
            if not employees:
                self.stdout.write(self.style.WARNING("Employee list is empty, skipping tax creation."))
                return
            for _ in range(50):
                Tax.objects.create(
                    employee=random.choice(employees),
                    income_tax=Decimal(f"{random.uniform(2000, 15000):.2f}"),
                    national_insurance=Decimal(f"{random.uniform(1000, 5000):.2f}"),
                    tax_year=random.choice([2023, 2024, 2025])
                )

        def create_pensions(employees):
            if not employees:
                self.stdout.write(self.style.WARNING("Employee list is empty, skipping pension creation."))
                return
            for _ in range(50):
                employee = random.choice(employees)  # Get a random employee
                employer_contribution_percent = Decimal(str(round(random.uniform(5, 10), 2)))
                employee_contribution_percent = Decimal(str(round(random.uniform(3, 8), 2)))

                # Calculate the actual contribution amounts
                employer_contribution_amount = Decimal(str(round(employee.salary * (employer_contribution_percent / 100), 2)))
                employee_contribution_amount = Decimal(str(round(employee.salary * (employee_contribution_percent / 100), 2)))

                Pension.objects.create(
                    employee=employee,
                    amount=Decimal(f"{random.uniform(3000, 20000):.2f}"),  # You might want to remove or recalculate this
                    employee_contribution=employee_contribution_amount,  # Store the calculated amount
                    employer_contribution_percent=employer_contribution_percent,  # Optionally store the percentage too
                    employee_contribution_percent=employee_contribution_percent,  # Optionally store the percentage too
                )

        def create_payrolls(employees):
            if not employees:
                self.stdout.write(self.style.WARNING("Employee list is empty, skipping payroll creation."))
                return
            for _ in range(50):
                emp = random.choice(employees)
                # Get the latest pension (you might need more complex logic here)
                latest_pension = Pension.objects.filter(employee=emp).order_by('-id').first()

                employee_pension_deduction = 0  # Default if no pension
                if latest_pension:
                    employee_pension_deduction = latest_pension.employee_contribution

                Payroll.objects.create(
                    employee=emp,
                    basic_salary=emp.salary,
                    bonus=Decimal(f"{random.uniform(0, 10000):.2f}"),
                    tax_amount=Decimal(f"{random.uniform(500, 10000):.2f}"),
                    pay_date=fake.date_this_year(),
                    pension_deduction=employee_pension_deduction,  # Add pension deduction
                    deduction = Decimal(f"{random.uniform(500, 10000):.2f}")
                    #net_salary=(
                            #emp.salary
                            #+ Decimal(f"{random.uniform(0, 10000):.2f}")
                            #- Decimal(f"{random.uniform(500, 10000):.2f}")
                    #)
                    # Example net salary calculation
                )

        def create_logs(users):
            actions = ['create', 'update', 'delete', 'login', 'logout', 'report_generate']
            models = ['Employee', 'Payroll', 'Bonus', 'Allowance', 'Deduction', 'User', 'Department', 'Position', 'RuleConfig']
            log_types = ['operation', 'system', 'security']
            for _ in range(50):
                Log.objects.create(
                    user_email=random.choice(users).email,
                    action=random.choice(actions)[:10],
                    model_name=random.choice(models)[:100],
                    object_id=random.randint(1, 50),
                    changes={"field": "value"},
                    log_type=random.choice(log_types)[:20]
                )

        def create_rules(users, departments):
            condition_types = ['rank', 'grade', 'department', 'salary_greater_than', 'salary_less_than']
            comparators = ['=', '>', '<', '>=', '<=']
            calculation_types = ['percent', 'fixed']
            for _ in range(50):
                rc = RuleConfig.objects.create(
                    name=fake.bs()[:100],
                    condition_type=random.choice(condition_types)[:20],
                    comparator=random.choice(comparators)[:2],
                    threshold=random.choice(['Analyst', 'B', departments[0].dept_name if departments else '', str(random.randint(50000, 200000))]),
                    calculation_type=random.choice(calculation_types)[:10],
                    value=Decimal(str(round(random.uniform(1, 20), 2) if random.choice(['percent']) == 'percent' else round(random.uniform(100, 5000), 2))),
                    created_by=random.choice(users),
                )
                rc.exclude_departments.set(random.sample(departments, k=random.randint(0, len(departments))))

        def create_salary_adjustment_approvals(employees):
            if not employees:
                self.stdout.write(self.style.ERROR("No employees found. Cannot create approvals."))
                return

            for _ in range(100):
                SalaryAdjustmentApproval.objects.create(
                    employee=random.choice(employees),
                    request_type=random.choice(['Bonus', 'Promotion', 'Adjustment']),
                    submitted_at=fake.date_time_between(start_date='-2M', end_date='now'),
                    status=random.choice(['pending', 'approved', 'rejected']),
                )
            self.stdout.write(self.style.SUCCESS("Successfully created 100 fake salary approvals."))

        # Reconnect the signal
        # post_save.connect(receiver=create_user_for_employee, sender=Employee)
        # Carry out all the generation
        departments = create_departments()
        positions = create_positions()
        users = create_users()
        employees = create_employees(users, departments, positions)
        create_bonuses(employees)
        create_allowances(employees)
        create_deductions(employees)
        create_taxes(employees)
        create_pensions(employees)
        create_payrolls(employees)
        create_logs(users)
        create_rules(users, departments)
        create_salary_adjustment_approvals(employees)

        print("All the data have been generated including salary adjustment approvals")
        self.stdout.write(self.style.SUCCESS('All the test data have been successfully generated'))
        utils.GENERATING_DATA = False  # Reset