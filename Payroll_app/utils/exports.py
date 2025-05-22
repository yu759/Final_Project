import base64
import io,csv
import logging
import pandas as pd
from django.utils.timezone import now
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from django.http import HttpResponse, HttpResponseBadRequest
from .charts import generate_trend_chart, generate_dept_chart, generate_heatmap_chart
from Payroll_app.models import Employee,Payroll,Department,Position
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
import os
from django.conf import settings

def generate_dashboard_pdf(data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    textobject = p.beginText(10, 750)
    textobject.setFont("Helvetica-Bold", 16)
    textobject.textLine("Dashboard Report")
    textobject.setFont("Helvetica", 12)
    textobject.textLine(f"Total Payroll This Month: £{data.get('total_payroll', 'N/A')}")
    textobject.textLine(f"Average Net Salary: £{data.get('avg_net_salary', 'N/A')}")
    textobject.textLine(f"Total Bonuses This Month: £{data.get('total_bonuses', 'N/A')}")
    textobject.textLine(f"Employee Count: {data.get('employee_count', 'N/A')}")
    textobject.textLine(f"Active Employees: {data.get('active_employees', 'N/A')}")
    textobject.textLine(f"Pending Adjustments: {data.get('pending_adjustments', 'N/A')}")
    textobject.textLine(f"Overdue Reports: {data.get('overdue_reports', 'N/A')}")
    p.drawText(textobject)
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def export_employee_pdf():
    from io import BytesIO
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("Employee Information Report", styles['Title'])
    elements.append(title)

    # Obtain employee information from the database
    employees = Employee.objects.all().values_list('employee_id', 'first_name', 'last_name', 'department__dept_name', 'position__name', 'is_active') # Changed to use first_name, last_name, department__dept_name, position__name, is_active based on models.py
    data = [('Employee ID', 'First Name', 'Last Name', 'Department', 'Position', 'Status')] + list(employees) # Updated header

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


def export_employee_csv():
    from io import StringIO
    buffer = StringIO()
    writer = csv.writer(buffer)

    # Table header
    writer.writerow(['Employee ID', 'First Name', 'Last Name', 'Department', 'Position', 'Status']) # Updated header

    # Get employee's  data
    employees = Employee.objects.all().values_list('employee_id', 'first_name', 'last_name', 'department__dept_name', 'position__name', 'is_active') # Changed to use first_name, last_name, department__dept_name, position__name, is_active based on models.py
    for emp in employees:
        writer.writerow(emp)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employees.csv"'
    return response

def generate_custom_employee_pdf(employees, fields):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    dept_groups = {}
    for emp in employees:
        dept_name = emp.department.dept_name if emp.department else "Unknown" # Corrected to use dept_name from Department model
        dept_groups.setdefault(dept_name, []).append(emp)

    for dept, emps in dept_groups.items():
        elements.append(Paragraph(f"Department: {dept}", styles['Heading2']))
        data = [fields]
        for emp in emps:
            row = []
            for field in fields:
                value = getattr(emp, field)
                # Handle foreign key objects if 'field' is a foreign key itself
                if field == 'department':
                    value = emp.department.dept_name if emp.department else "N/A" # Corrected to use dept_name from Department model
                elif field == 'position':
                    value = emp.position.name if emp.position else "N/A" # Assuming Position model has a 'name' field
                elif hasattr(value, '__str__'):
                    value = str(value)
                row.append(value)
            data.append(row)

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

    doc.build(elements)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


def export_chart_as_pdf(chart_buffer_bytes=None):
    """Embed the PNG chart into a PDF file"""
    response: HttpResponse = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="salary_report.pdf"'

    c = canvas.Canvas(response, pagesize=letter)

    image = ImageReader(io.BytesIO(chart_buffer_bytes))

    c.drawImage(image, 50, 500, width=500, height=300)  # Position may be adjusted
    c.showPage()
    c.save()

    return response


def export_salary_csv(df):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="salary_data.csv"'
    return response

def generate_custom_employee_csv(employees, fields):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(fields)

    for emp in employees:
        row = []
        for field in fields:
            value = getattr(emp, field)
            # Handle foreign key objects if 'field' is a foreign key itself
            if field == 'department':
                value = emp.department.dept_name if emp.department else "N/A" # Corrected to use dept_name from Department model
            elif field == 'position':
                value = emp.position.name if emp.position else "N/A" # Assuming Position model has a 'name' field
            elif hasattr(value, '__str__'):
                value = str(value)
            row.append(value)
        writer.writerow(row)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employees.csv"'
    return response


def export_all_charts_pdf():
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "Payroll Chart Report")

    y = 700
    spacing = 250

    # Generate an ImageReader object using base64 image data and insert it into a PDF
    chart_funcs = [
        generate_trend_chart,
        lambda: generate_dept_chart(Employee.objects.all()),
        generate_heatmap_chart
    ]

    for chart_func in chart_funcs:
        image_base64 = chart_func()
        if image_base64:

            base64_data = image_base64.split(',')[1]
            image_data = base64.b64decode(base64_data)
            image_io = io.BytesIO(image_data)
            image_reader = ImageReader(image_io)

            # Check whether pagination is needed
            if y < 200:
                p.showPage()
                y = 700

            p.drawImage(image_reader, 100, y - 200, width=400, height=200)
            y -= spacing

    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

def generate_salary_export(date_from, date_to, format='csv'):
    logging.info(f"Generating salary export. Date from: {date_from}, Date to: {date_to}, Format: {format}")
    try:
        logging.info(f"Date from type: {type(date_from)}, value: {date_from}")
        logging.info(f"Date to type: {type(date_to)}, value: {date_to}")

        # --- Data Retrieval ---
        if date_from and date_to:
            salary_data = Payroll.objects.filter(
                pay_date__range=(date_from, date_to)
            ).values(  # Specify the fields you need
                'employee_id', # Changed from 'employee__employee_id' to 'employee_id'
                'employee__first_name',
                'employee__last_name',
                'pay_date',
                'basic_salary',
                'bonus',
            )
            logging.info(f"Retrieved {salary_data.count()} salary records with date filter.")
        else:
            salary_data = Payroll.objects.all().values(  # Specify the fields
                'employee_id', # Changed from 'employee__employee_id' to 'employee_id'
                'employee__first_name',
                'employee__last_name',
                'pay_date',
                'basic_salary',
                'bonus',
            )
            logging.info(f"Retrieved {salary_data.count()} total salary records.")

        data = list(salary_data)
        logging.info(f"Data sample: {data[:5]}")  # Log a sample of the data

        df = pd.DataFrame(data)

        # --- CSV Export ---
        if format == 'csv':
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="salary_data.csv"'
            logging.info("CSV export successful.")
            return response

        # --- PDF Export ---
        elif format == 'pdf':
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            title = Paragraph("Wage data report", styles['Title'])
            elements.append(title)

            table_data = [list(df.columns)] + df.values.tolist()
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            elements.append(table)
            doc.build(elements)
            buffer.seek(0)
            logging.info("PDF export successful.")
            return HttpResponse(buffer, content_type='application/pdf')

        else:
            raise ValueError("Invalid export format")

    except Exception as e:
        logging.error(f"Error generating salary export: {e}", exc_info=True)
        return HttpResponse("Error generating export.", status=500)

def generate_employee_export(format='csv', fields=None, departments=None):
    logging.info(f"Generating employee export. Format: {format}, Fields: {fields}, Departments: {departments}")
    try:
        employees = Employee.objects.all()

        if departments:
            employees = employees.filter(department__id__in=departments)

        if not fields:
            all_fields = [field.name for field in Employee._meta.get_fields() if field.name not in ['id', 'user']]
            fields_to_export = []
            for field_name in all_fields:
                if field_name == 'position':
                    fields_to_export.append('position__name')
                elif field_name == 'department':
                    fields_to_export.append('department__dept_name') # Corrected to dept_name based on models.py
                elif field_name in ['allowances', 'deductions', 'pensions', 'payroll', 'performance', 'salaryadjustmentapproval']:
                    continue
                else:
                    fields_to_export.append(field_name)
            fields = fields_to_export


        employee_data = list(employees.values(*fields))
        df = pd.DataFrame(employee_data)

        if format == 'csv':
            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            response = HttpResponse(buffer.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="employee_info.csv"'
            return response
        elif format == 'pdf':
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            title = Paragraph("Employee Information", styles['Title'])
            elements.append(title)

            # Prepare data for the table, ensuring there's at least a header row
            if df.empty:
                data = [fields]
                logging.warning("No employee data to export. Creating PDF with only headers.")
            else:
                data = [df.columns.tolist()]
                for _, row in df.iterrows():
                    data_row = []
                    for field in df.columns:
                        value = row[field]
                        data_row.append(str(value) if pd.notna(value) else '')

                    data.append(data_row)

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            doc.build(elements)
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="employee_info.pdf"'
            return response
        else:
            return HttpResponseBadRequest("Invalid export format.", content_type="text/plain")

    except Exception as e:
        logging.error(f"Error generating employee export: {e}", exc_info=True)
        return HttpResponse("Error generating export.", status=500, content_type="text/plain")

def generate_salary_trend_chart():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1000, 2000, 1500])
    ax.set_title("Salary Trend")

    # Save the image to the MEDIA folder
    image_path = os.path.join(settings.MEDIA_ROOT, 'salary_trend.png')
    fig.savefig(image_path)

    return image_path

def export_salary_data(format, time_range, start_date=None, end_date=None):
    try:
        # Obtain all salary data
        payroll_data = Payroll.objects.all()

        # Filter according to the time range
        if time_range == 'monthly':
            payroll_data = payroll_data.filter(pay_date__month=now().month)
        elif time_range == 'yearly':
            payroll_data = payroll_data.filter(pay_date__year=now().year)
        elif time_range == 'custom' and start_date and end_date:
            payroll_data = payroll_data.filter(pay_date__range=(start_date, end_date))

        # Prepare to export the data (adjust the fields as needed
        data = []
        for payroll in payroll_data:
            employee_obj = payroll.employee
            base_salary = employee_obj.salary if employee_obj and employee_obj.salary is not None else 0
            bonus = payroll.bonus if payroll.bonus is not None else 0
            total_allowance = sum(allowance.amount for allowance in employee_obj.allowances.all()) if employee_obj else 0
            total_deduction = sum(deduction.amount for deduction in employee_obj.deductions.all()) if employee_obj else 0
            net_salary = payroll.net_salary

            data.append({
                'employee_name': employee_obj.first_name + ' ' + employee_obj.last_name,
                'pay_date': payroll.pay_date,
                'base_salary': payroll.basic_salary,
                'bonus': payroll.bonus,
                'allowance': payroll.allowances_total,
                'deduction': payroll.deductions_total,
                'net_salary': payroll.net_salary,
            })
        df = pd.DataFrame(data)

        if format == 'csv':
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="salary_data.csv"'
            return response
        elif format == 'pdf':
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            title = Paragraph("Wage data report", styles['Title'])
            elements.append(title)

            table_data = [list(df.columns)] + df.values.tolist()
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            elements.append(table)
            doc.build(elements)
            buffer.seek(0)
            return HttpResponse(buffer, content_type='application/pdf')
        else:
            return HttpResponse("Invalid format.", status=400)

    except Exception as e:
        return HttpResponse(f"There was an error in exporting the salary data: {e}", status=500)
