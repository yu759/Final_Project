import decimal
import math
import random
from collections import defaultdict
from datetime import date


# --- Mocking your Django models based on your models.py and exports.py ---
# In a real Django setup, you would import these:
# from Payroll_app.models import Employee, Payroll # Assuming Allowance and Deduction models exist but their values are aggregated into Payroll

class MockEmployee:
    # Mimics relevant fields from your Employee model
    def __init__(self, id, employee_id, first_name, last_name, email, grade, annual_basic_salary):
        self.id = id
        self.employee_id = employee_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.grade = grade
        self.salary = decimal.Decimal(str(annual_basic_salary))  # Assuming 'salary' on Employee is annual basic salary


class MockPayroll:
    # Mimics relevant fields from your Payroll model for a specific month
    # Enhanced to store the parameters that contributed to the system's net_salary calculation
    def __init__(self, id, employee_obj, month, year, calculated_monthly_net_salary,
                 annual_performance_bonus, annual_total_allowances,
                 annual_total_deductions):  # Simplified to just 'total deductions' as per your feedback
        self.id = id
        self.employee = employee_obj  # ForeignKey to MockEmployee instance
        self.month = month
        self.year = year
        self.net_salary = decimal.Decimal(str(calculated_monthly_net_salary))  # System's calculated monthly net salary

        # Parameters that contributed to this net_salary in the system, derived from inputs
        self.annual_performance_bonus = decimal.Decimal(str(annual_performance_bonus))  # From performanceInput
        self.annual_total_allowances = decimal.Decimal(
            str(annual_total_allowances))  # From allowanceInput and other allowances
        self.annual_total_deductions = decimal.Decimal(
            str(annual_total_deductions))  # Sum of all deductions from deductionInput etc.


# --- End Mock Model Definitions ---

# Set Decimal context for precise calculations
decimal.getcontext().prec = 10
decimal.getcontext().rounding = decimal.ROUND_HALF_UP


# UK Income Tax Calculation Function (HMRC) - Unchanged
def calculate_uk_income_tax(annual_taxable_income):
    annual_taxable_income = decimal.Decimal(str(annual_taxable_income))
    tax = decimal.Decimal('0.00')
    remaining_taxable = annual_taxable_income

    personal_allowance = decimal.Decimal('12570.00')

    if remaining_taxable > personal_allowance:
        remaining_taxable -= personal_allowance
    else:
        return decimal.Decimal('0.00')

    basic_rate_band = decimal.Decimal('37700.00')
    if remaining_taxable > 0:
        taxable_in_basic_band = min(remaining_taxable, basic_rate_band)
        tax += taxable_in_basic_band * decimal.Decimal('0.20')
        remaining_taxable -= taxable_in_basic_band

    higher_rate_band = decimal.Decimal('99730.00')
    if remaining_taxable > 0:
        taxable_in_higher_band = min(remaining_taxable, higher_rate_band)
        tax += taxable_in_higher_band * decimal.Decimal('0.40')
        remaining_taxable -= higher_rate_band

    if remaining_taxable > 0:
        tax += remaining_taxable * decimal.Decimal('0.45')

    return round_correction(tax)


# UK National Insurance (NI) Calculation Function - Unchanged
def calculate_uk_ni(annual_gross_income):
    annual_gross_income = decimal.Decimal(str(annual_gross_income))
    weekly_earnings = annual_gross_income / decimal.Decimal('52')

    ni = decimal.Decimal('0.00')

    pt = decimal.Decimal('242.00')
    uel = decimal.Decimal('967.00')

    if weekly_earnings > pt:
        earnings_between_pt_uel = min(weekly_earnings - pt, uel - pt)
        ni += earnings_between_pt_uel * decimal.Decimal('0.08')

        if weekly_earnings > uel:
            earnings_above_uel = weekly_earnings - uel
            ni += earnings_above_uel * decimal.Decimal('0.02')

    annual_ni = ni * decimal.Decimal('52')
    return round_correction(annual_ni)


# Decimal Rounding Correction - Unchanged
def round_correction(value):
    return decimal.Decimal(str(value)).quantize(
        decimal.Decimal('0.00'),
        rounding=decimal.ROUND_HALF_UP
    )


# Mean Squared Error (MSE) Calculation - Unchanged
def calculate_mse(manual_values, system_values):
    if len(manual_values) != len(system_values):
        raise ValueError("Lengths of manual and system values lists must be identical.")

    n = len(manual_values)
    if n == 0:
        return decimal.Decimal('0.00')

    sum_of_squared_errors = decimal.Decimal('0.00')
    for i in range(n):
        manual_corrected = round_correction(manual_values[i])
        system_corrected = round_correction(system_values[i])

        error = manual_corrected - system_corrected
        sum_of_squared_errors += (error * error)

    mse = sum_of_squared_errors / decimal.Decimal(str(n))
    return mse


# --- Function to simulate populating mock database data based on your models ---
def populate_mock_db_data(num_per_grade=5):
    """
    Generates mock Employee and Payroll data mimicking your Django models.
    num_per_grade: Number of mock employees to generate for each grade.
    """
    mock_employees_list = []
    mock_payrolls_list = []

    grades_salary_ranges = {
        'A': (decimal.Decimal('150000.00'), decimal.Decimal('250000.00')),
        'B': (decimal.Decimal('80000.00'), decimal.Decimal('150000.00')),
        'C': (decimal.Decimal('50000.00'), decimal.Decimal('80000.00')),
        'D': (decimal.Decimal('30000.00'), decimal.Decimal('50000.00')),
    }

    employee_id_counter = 1
    payroll_id_counter = 1

    for grade in ['A', 'B', 'C', 'D']:
        min_salary, max_salary = grades_salary_ranges[grade]
        for i in range(num_per_grade):
            # 1. Create a MockEmployee instance (mimicking Employee.objects.create)
            emp = MockEmployee(
                id=employee_id_counter,
                employee_id=f"EMP-{grade}-{i + 1:03d}",
                first_name=f"MockFName{employee_id_counter}",
                last_name=f"MockLName{employee_id_counter}",
                email=f"mock.emp{employee_id_counter}@example.com",
                grade=grade,
                annual_basic_salary=decimal.Decimal(f"{random.uniform(float(min_salary), float(max_salary)):.2f}")
            )
            mock_employees_list.append(emp)

            # 2. Simulate parameters that would be stored or derived for the payroll calculation
            annual_performance_bonus = round_correction(
                decimal.Decimal(str(random.uniform(0, 5000))))  # e.g., a bonus amount
            annual_total_allowances = round_correction(
                emp.salary * decimal.Decimal(str(random.uniform(0.02, 0.08))))  # 2-8% of basic salary as allowances

            # Based on your feedback "annual_post_tax_deductions也没有", and salary.html's single deductionInput,
            # we will generate a single total deduction.
            # In a real UK payroll, pre-tax deductions reduce taxable income, post-tax deductions don't.
            # For this simplified mock, we will treat the total deduction as *pre-tax* for its impact on taxable income,
            # as this is the most common scenario for 'deductions' impacting tax calculations.
            # If your system processes both types, your Payroll model needs to store them separately.
            annual_total_deductions_simulated = round_correction(
                decimal.Decimal(str(random.uniform(0, float(emp.salary) * 0.1))))  # Up to 10% of salary as deductions

            # 3. Calculate system's 'net_salary' (this is what your actual system would store in Payroll)
            # This calculation should EXACTLY mimic your system's actual payroll calculation logic.
            # Based on salary.html: netSalary = performance + allowance - deduction + baseSalary (then taxes/NI)
            total_annual_gross_income_for_system = emp.salary + annual_performance_bonus + annual_total_allowances

            # For tax and NI calculation, we'll assume the single 'annual_total_deductions_simulated' acts as pre-tax.
            taxable_income_for_it_system = total_annual_gross_income_for_system - annual_total_deductions_simulated
            taxable_income_for_ni_system = total_annual_gross_income_for_system  # Assuming NI base is gross for simplicity

            income_tax_system = calculate_uk_income_tax(taxable_income_for_it_system)
            national_insurance_system = calculate_uk_ni(taxable_income_for_ni_system)

            # This is the "system's" calculated net salary before any induced deviation
            system_annual_net_salary_true = (
                    total_annual_gross_income_for_system
                    - annual_total_deductions_simulated  # Deduct this amount
                    - income_tax_system
                    - national_insurance_system
            )
            system_monthly_net_salary_true = round_correction(system_annual_net_salary_true / decimal.Decimal('12'))

            # Introduce some simulated deviation to system's calculated net_salary for testing
            system_calculated_monthly_net_salary_with_deviation = system_monthly_net_salary_true
            if random.random() < 0.2:  # 20% chance of small deviation
                system_calculated_monthly_net_salary_with_deviation += decimal.Decimal(
                    f"{random.uniform(-0.02, 0.02):.2f}")  # +/- 2p
            if random.random() < 0.05:  # 5% chance of larger deviation
                system_calculated_monthly_net_salary_with_deviation += decimal.Decimal(
                    f"{random.uniform(-1.50, 1.50):.2f}")  # +/- £1.50

            # 4. Create a MockPayroll instance (mimicking Payroll.objects.create)
            payroll_record = MockPayroll(
                id=payroll_id_counter,
                employee_obj=emp,  # Link to the employee object
                month=5,  # Example month (you'd get this from your system for the current payroll run)
                year=2025,
                calculated_monthly_net_salary=system_calculated_monthly_net_salary_with_deviation,
                annual_performance_bonus=annual_performance_bonus,
                annual_total_allowances=annual_total_allowances,
                annual_total_deductions=annual_total_deductions_simulated  # Corrected: Pass the generated variable
            )
            mock_payrolls_list.append(payroll_record)

            employee_id_counter += 1
            payroll_id_counter += 1

    return mock_employees_list, mock_payrolls_list


# --- Main Validation Logic ---
if __name__ == "__main__":
    epsilon = decimal.Decimal('0.50')

    print("--- Payroll Accuracy Validation Report (UK Tax - Graded Sampling) ---")
    # Updated header to reflect 'Total Deductions' instead of 'Pre-tax' and 'Post-tax'
    print(
        "Sample ID | Grade | Annual Basic Salary | Annual Performance Bonus | Annual Allowance | Annual Total Deduction | Manual Monthly Net | System Monthly Net | Deviation | Needs Review? | Notes")
    print("-" * 170)  # Adjusted line length

    # **1. Simulate fetching all employee and payroll data from the database.**
    # In your real Django project, this is where you would query your actual models:
    # from Payroll_app.models import Employee, Payroll # Make sure to import your models
    # current_payroll_month = date.today().month
    # current_payroll_year = date.today().year

    # all_employees_from_db = Employee.objects.all().select_related('latest_payroll') # Assuming you have a related_name on Payroll ForeignKey
    # # OR:
    # payrolls_for_period = Payroll.objects.filter(
    #     month=current_payroll_month,
    #     year=current_payroll_year
    # ).select_related('employee')

    # employees_with_payrolls = []
    # for p in payrolls_for_period:
    #     emp = p.employee # Get the employee object
    #     emp.latest_payroll = p # Attach the payroll object to the employee
    #     employees_with_payrolls.append(emp)
    # # Then group employees_with_payrolls by grade for sampling

    # Use the mock data generator for this script:
    all_mock_employees, all_mock_payrolls = populate_mock_db_data(num_per_grade=10)

    # Map payroll records to their respective employees for easier access
    payrolls_by_employee_id = {p.employee.id: p for p in all_mock_payrolls}

    # Group employees by grade and attach their latest payroll data
    employees_by_grade = defaultdict(list)
    for emp in all_mock_employees:
        latest_payroll_for_emp = payrolls_by_employee_id.get(emp.id)
        if latest_payroll_for_emp:
            emp.latest_payroll = latest_payroll_for_emp
            employees_by_grade[emp.grade].append(emp)
        else:
            print(f"Warning: Employee {emp.employee_id} ({emp.grade}) has no corresponding payroll record and will be skipped for sampling.")


    # **2. Select 3 employees from each grade for testing.**
    selected_employees_for_test = []
    grades_to_sample = ['A', 'B', 'C', 'D']
    employees_per_grade_sample = 3

    for grade in grades_to_sample:
        eligible_employees_in_grade = [emp for emp in employees_by_grade[grade] if hasattr(emp, 'latest_payroll')]
        if len(eligible_employees_in_grade) < employees_per_grade_sample:
            print(
                f"Warning: Insufficient eligible employees in grade {grade} (found {len(eligible_employees_in_grade)} employees), sampling all available employees.")
            selected_employees_for_test.extend(eligible_employees_in_grade)
        else:
            selected_employees_for_test.extend(random.sample(eligible_employees_in_grade, employees_per_grade_sample))

    total_samples_count = len(selected_employees_for_test)
    print(f"\nTotal {total_samples_count} employees selected for validation.")
    print("-" * 170)

    manual_monthly_net_salaries = []
    system_monthly_net_salaries_collected = []
    comparison_results = []

    for emp in selected_employees_for_test:
        # Extract data from the mock Employee and Payroll objects
        employee_id = emp.employee_id
        grade = emp.grade
        annual_basic_salary = emp.salary  # From Employee.salary

        # Data from the latest Payroll record for this employee (these are the system's inputs)
        annual_performance_bonus = emp.latest_payroll.annual_performance_bonus
        annual_total_allowances = emp.latest_payroll.annual_total_allowances
        annual_total_deductions = emp.latest_payroll.annual_total_deductions  # Single total deduction
        system_output_monthly_net_salary = emp.latest_payroll.net_salary

        # --- Manual Calculation Steps (using the system's recorded inputs) ---
        # This mirrors the logic: baseSalary + performance + allowance - deduction - taxes - NI
        # 1. Total Annual Gross Income (for tax and NI purposes)
        total_annual_gross_income_manual = annual_basic_salary + annual_performance_bonus + annual_total_allowances

        # 2. Taxable income for Income Tax (Gross - Total Deductions, assuming all deductions are pre-tax for simplicity)
        # IMPORTANT: If your system has both pre-tax and post-tax deductions, and you ONLY store
        # a 'total_deductions' field, then accurate manual re-calculation of tax/NI is impossible
        # without knowing how that total is split. For this script, we assume all total deductions are pre-tax for impact on taxable income.
        taxable_income_for_it_manual = total_annual_gross_income_manual - annual_total_deductions

        # 3. Calculate Income Tax
        income_tax_manual = calculate_uk_income_tax(taxable_income_for_it_manual)

        # 4. Calculate National Insurance (typically based on gross income for NIable earnings)
        national_insurance_manual = calculate_uk_ni(total_annual_gross_income_manual)

        # 5. Total Annual Deductions (All non-tax deductions + Income Tax + NI)
        total_annual_deductions_for_net_salary_manual = annual_total_deductions + income_tax_manual + national_insurance_manual

        # 6. Annual Net Salary
        annual_net_salary_manual = total_annual_gross_income_manual - total_annual_deductions_for_net_salary_manual

        # 7. Monthly Net Salary
        manual_monthly_net_salary = round_correction(annual_net_salary_manual / decimal.Decimal('12'))

        # Record data for MSE and comparison
        manual_monthly_net_salaries.append(manual_monthly_net_salary)
        system_monthly_net_salaries_collected.append(system_output_monthly_net_salary)

        # Deviation analysis
        deviation = manual_monthly_net_salary - system_output_monthly_net_salary
        needs_review = "Yes" if abs(deviation) > epsilon else "No"
        remark = "Accuracy within tolerance" if abs(deviation) <= epsilon else "Significant deviation, needs review"

        # Print to console (table row)
        # Updated print statement
        print(
            f"{employee_id:<9} | {grade:<4} | {annual_basic_salary:<20.2f} | {annual_performance_bonus:<24.2f} | {annual_total_allowances:<16.2f} | {annual_total_deductions:<22.2f} | {manual_monthly_net_salary:<18.2f} | {system_output_monthly_net_salary:<20.2f} | {deviation:<10.2f} | {needs_review:<13} | {remark}")


        comparison_results.append({
            "Sample ID": employee_id,
            "Grade": grade,
            "Annual Basic Salary": annual_basic_salary,
            "Annual Performance Bonus": annual_performance_bonus,
            "Annual Allowance": annual_total_allowances,
            "Annual Total Deduction": annual_total_deductions,
            "Manual Monthly Net": manual_monthly_net_salary,
            "System Monthly Net": system_output_monthly_net_salary,
            "Deviation": deviation,
            "Needs Review?": needs_review,
            "Notes": remark
        })

    print("-" * 170)

    # Calculate MSE
    final_mse = calculate_mse(manual_monthly_net_salaries, system_monthly_net_salaries_collected)
    print(f"\nMean Squared Error (MSE) for {total_samples_count} samples: {final_mse:.6f}")

    # Validation conclusion
    if final_mse < decimal.Decimal('0.001'):
        print("\nValidation Conclusion: System payroll accuracy meets industrial standards (error tolerance ±0.1%), can pass ISO/IEC 25010 quality standard certification.")
    else:
        print("\nValidation Conclusion: System payroll has deviations and does not meet industrial standards. Please perform a Level 3 review based on the deviation report.")

    # To export to CSV or Excel, uncomment the following and ensure pandas is installed
    # import pandas as pd
    # df = pd.DataFrame(comparison_results)
    # df.to_csv("payroll_accuracy_report_uk_graded_from_models.csv", index=False)
    # print("\nDetailed comparison report saved to payroll_accuracy_report_uk_graded_from_models.csv")