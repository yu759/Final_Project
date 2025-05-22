import io
import base64
import calendar
import os

import pandas as pd
import matplotlib.pyplot as plt
from django.db.models import Sum, Count
from matplotlib.figure import Figure
from django.db.models.functions import TruncMonth

from Final_Project import settings
from Payroll_app.models import Payroll, Employee
import plotly.express as px
import plotly.graph_objects as go
from django.utils.timezone import now

# General Rendering Function
def render_chart(fig: Figure) -> str:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{image_base64}"


# Monthly salary trend Chart (Green bar chart)
def generate_trend_chart() -> str:
    payrolls = Payroll.objects.filter(pay_date__isnull=False).annotate(month=TruncMonth('pay_date'))
    if not payrolls.exists():
        return ""

    df = pd.DataFrame(list(payrolls.values('month')))
    df['basic_salary'] = [float(p.employee.salary or 0) for p in
                          Payroll.objects.filter(pay_date__isnull=False)]  # 获取基本工资
    df['bonus'] = [float(p.bonus or 0) for p in Payroll.objects.filter(pay_date__isnull=False)]  # 获取奖金

    df['total_allowances'] = [
        float(sum(a.amount for a in p.employee.allowances.all()))
        for p in Payroll.objects.filter(pay_date__isnull=False)
    ]
    df['total_deductions'] = [
        float(sum(d.amount for d in p.employee.deductions.all()))
        for p in Payroll.objects.filter(pay_date__isnull=False)
    ]

    df['net_salary'] = df['basic_salary'] + df['bonus'] + df['total_allowances'] - df['total_deductions']
    df['month'] = pd.to_datetime(df['month'])
    monthly_total = df.groupby('month')['net_salary'].sum().sort_index()

    fig, ax = plt.subplots()
    monthly_total.plot(kind='bar', ax=ax, color='green')
    ax.set_title("Monthly Payroll Trend")
    ax.set_ylabel("Total Net Salary")
    ax.set_xlabel("Month")
    ax.set_xticklabels([m.strftime('%b %Y') for m in monthly_total.index], rotation=45)

    return render_chart(fig)


# Department Staff Distribution Map (Pie Chart)
def generate_dept_chart(employees=None) -> str:
    if employees is None:
        employees = Employee.objects.select_related('department').all()
    df = pd.DataFrame(list(employees.values('department__dept_name')))
    if df.empty:
        return ""

    counts = df['department__dept_name'].value_counts()
    fig, ax = plt.subplots()
    wedges, texts, autotexts = ax.pie(counts, autopct='%1.1f%%', startangle=90, textprops=dict(color="black"))
    ax.legend(wedges, counts.index, title="Departments", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    ax.set_title('Employee Department Distribution')
    plt.setp(autotexts, size=8, weight="bold")
    ax.set_ylabel('')

    return render_chart(fig)


# Annual heat map (Orange bar chart)
def generate_heatmap_chart() -> str:
    current_year = now().year
    payrolls = Payroll.objects.filter(pay_date__year=current_year)
    if not payrolls.exists():
        return ""

    df = pd.DataFrame(list(payrolls.values('pay_date')))
    df['basic_salary'] = [float(p.employee.salary or 0) for p in
                          Payroll.objects.filter(pay_date__isnull=False)]  # 获取基本工资
    df['bonus'] = [float(p.bonus or 0) for p in Payroll.objects.filter(pay_date__isnull=False)]  # 获取奖金

    df['total_allowances'] = [
        float(sum(a.amount for a in p.employee.allowances.all()))
        for p in Payroll.objects.filter(pay_date__isnull=False)
    ]
    df['total_deductions'] = [
        float(sum(d.amount for d in p.employee.deductions.all()))
        for p in Payroll.objects.filter(pay_date__isnull=False)
    ]

    df['net_salary'] = df['basic_salary'] + df['bonus'] + df['total_allowances'] - df['total_deductions']
    df['month'] = pd.to_datetime(df['pay_date']).dt.month
    monthly_total = df.groupby('month')['net_salary'].sum().reindex(range(1, 13), fill_value=0)

    fig, ax = plt.subplots()
    monthly_total.plot(kind='bar', ax=ax, color='orange')
    ax.set_title(f'Monthly Payroll Trend ({current_year})')
    ax.set_xlabel('Month')
    ax.set_ylabel('Total Payroll')
    ax.set_xticks(range(0, 12))
    ax.set_xticklabels([calendar.month_abbr[i + 1] for i in range(12)])

    return render_chart(fig)


# Custom Salary Chart (for personal and sample data)
def generate_salary_trend_chart(df: pd.DataFrame) -> bytes:
    try:
        df['salary'] = pd.to_numeric(df['salary'])
    except Exception as e:
        print(f"Error converting 'salary' to numeric: {e}")
        return b''

    fig, ax = plt.subplots(figsize=(10, 6))
    df.plot(kind='bar', x='name', y='salary', ax=ax, legend=False)
    ax.set_title('Salary Trend')
    ax.set_xlabel('Employee Name')
    ax.set_ylabel('Salary')
    ax.set_xticklabels(df['name'], rotation=45, ha='right')

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(os.path.join(settings.MEDIA_ROOT, 'chart.png'))
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


# Chart Type Mapping Scheduler
def generate_chart_image(chart_type: str, employees=None):
    chart_map = {
        'trend_chart': generate_trend_chart,
        'dept_chart': lambda: generate_dept_chart(employees),
        'heatmap_chart': generate_heatmap_chart,
    }
    func = chart_map.get(chart_type)
    if func:
        return func()
    return ""


def get_trend_chart():
    qs = Payroll.objects.all().values('pay_date').annotate(total_basic_salary=Sum('employee__salary'),
    total_bonus=Sum('bonus'),).order_by('pay_date')
    df = pd.DataFrame(list(qs))

    # Calculate total_allowances and total_deductions, grouped by pay_date
    allowance_dict = {}
    deduction_dict = {}

    for payroll in Payroll.objects.all():
        pay_date = payroll.pay_date
        allowance_sum = sum(
        allowance.amount for allowance in payroll.employee.allowances.all()) if payroll.employee else 0
        deduction_sum = sum(
        deduction.amount for deduction in payroll.employee.deductions.all()) if payroll.employee else 0

        if pay_date not in allowance_dict:
            allowance_dict[pay_date] = 0
        if pay_date not in deduction_dict:
            deduction_dict[pay_date] = 0

        allowance_dict[pay_date] += allowance_sum
        deduction_dict[pay_date] += deduction_sum

    total_allowances = [allowance_dict.get(pay_date, 0) for pay_date in df['pay_date']]
    total_deductions = [deduction_dict.get(pay_date, 0) for pay_date in df['pay_date']]

    df['total_allowances'] = total_allowances
    df['total_deductions'] = total_deductions

    df['total_net_salary'] = df['total_basic_salary'] + df['total_bonus'] + df['total_allowances'] - df[
        'total_deductions']
    fig = px.line(df, x='pay_date', y='total_net_salary', title='Monthly Payroll Trend')
    return fig.to_html(full_html=False)

def get_dept_distribution_chart():
    qs = Employee.objects.values('department__dept_name').annotate(count=Count('id'))
    df = pd.DataFrame(qs)
    fig = px.pie(df, names='department__dept_name', values='count', title='Employees by Department')
    return fig.to_html(full_html=False)

def get_annual_heatmap():
    # Obtain the required fields
    qs = Payroll.objects.all().select_related('employee').values('pay_date', 'basic_salary','bonus', 'employee_id', 'employee__salary')
    df = pd.DataFrame(list(qs))# The QuerySet needs to be converted to a list

    # Calculate net_salary
    if 'employee__salary' in df.columns:
        df['basic_salary'] = df['employee__salary']
    else:
        df['basic_salary'] = 0
    df = pd.DataFrame(list(qs))
    df['bonus'] = list(Payroll.objects.all().values_list('bonus', flat=True))
    df['total_allowances'] = df['employee_id'].apply(
        lambda emp_id: sum(a.amount for a in Employee.objects.get(id=emp_id).allowances.all())
    )
    df['total_deductions'] = df['employee_id'].apply(
        lambda emp_id: sum(d.amount for d in Employee.objects.get(id=emp_id).deductions.all())
    )
    df['net_salary'] = df['basic_salary'] + df['bonus'] + df['total_allowances'] - df['total_deductions']

    df['month'] = pd.to_datetime(df['pay_date']).dt.month
    df['day'] = pd.to_datetime(df['pay_date']).dt.day  # Corrected line
    pivot_df = df.pivot_table(index='month', columns='day', values='net_salary', fill_value=0)
    fig = go.Figure(data=go.Heatmap(z=pivot_df.values, x=pivot_df.columns, y=pivot_df.index, colorscale='Viridis'))
    fig.update_layout(title='Annual Payroll Heatmap', yaxis_title='Month', xaxis_title='Day')
    return fig.to_html(full_html=False)
