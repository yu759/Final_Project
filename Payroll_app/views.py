import csv,json,logging,matplotlib
import random
from datetime import datetime
from venv import logger
from django.utils import timezone
current_time = timezone.now()
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from sklearn.ensemble import IsolationForest
from Payroll_app import utils
from Payroll_app.utils.exports import export_all_charts_pdf, export_chart_as_pdf, export_salary_csv, generate_salary_export, generate_employee_export, generate_dashboard_pdf
from Payroll_app.utils.charts import get_trend_chart, get_dept_distribution_chart, get_annual_heatmap
from Payroll_app.utils.dashboard_data import get_dashboard_stats
from Payroll_app.utils.user_settings import api_response, approval_to_dict
matplotlib.use('Agg')  # Use the Agg backend
import matplotlib.pyplot as plt
import pandas as pd
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import caches
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from Payroll_app.forms import EmployeeAdminRegisterForm
from Payroll_app.models import Employee, Payroll, Department, CustomUser, Position, RuleConfig, Allowance, Log, \
    Deduction, APIKey, Approval, SalaryAdjustmentApproval
from django.contrib.auth import authenticate, login, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.http import JsonResponse
from Payroll_app.utils.charts import generate_salary_trend_chart

@cache_page(60 * 15)  # Cache for 15 minutes
def my_view(request):
    cache = caches['default']

#Register page
@csrf_exempt
def admin_check(user):
    return user.is_authenticated and user.role == CustomUser.ADMIN

@user_passes_test(admin_check, login_url='/login/')
def register_employee(request):
    if request.method == 'GET':
        form = EmployeeAdminRegisterForm()
        return render(request, 'add_new_user_form.html', {
            "form":form,
            "departments": Department.objects.all(),
            "positions": Position.objects.all(),
        })

    elif request.method == 'POST':
        form = EmployeeAdminRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            data = request.POST
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
            else:
                try:
                    with transaction.atomic():
                        # Create CustomUser
                        user = CustomUser.objects.create_user(
                            email=email,
                            password=None,#temporary password
                            role=CustomUser.USER
                        )
                        hire_date=parse_date(data.get('hire_date'))

                        # Create Employee case
                        employee = Employee.objects.create(
                            user=user,
                            first_name=data.get('first_name'),
                            last_name=data.get('last_name'),
                            email=email,
                            hire_date=hire_date,
                            salary=data.get('salary'),
                            department=data.get('department'),
                            position=data.get('position'),
                            rank=data.get('rank', 'junior'),
                            grade=data.get('grade', 'C')
                        )

                        # Generate and set a new password
                        pw = employee.generate_password()
                        user.set_password(pw)
                        user.save()

                        #Send email notifications
                        send_mail(
                            subject="Your Account Password",
                            message=f"Welcome {employee.first_name},\n\nYour account has been created.\nYour login password is: {pw}\nPlease log in and change it.",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False
                        )

                        messages.success(request, "Employee registered successfully.")
                        return redirect('employee_list')

                except Exception as e:
                    logging.exception("Failed to register employee")
                    messages.error(request, f"Registration failed: {e}")
                    return render(request, 'add_new_user_form.html', {
                        "form": form,
                        "departments": Department.objects.all(),
                        "positions": Position.objects.all(),
                    })
            return render(request, 'add_new_user_form.html', {
                "form": form,
                "departments": Department.objects.all(),
                "positions": Position.objects.all(),
            })

#Login page
User = get_user_model()
class CustomLoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    #@method_decorator(csrf_exempt, name='dispatch')
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
                email = data.get("email")
                password = data.get("password")
                next_url = data.get('next', '/')

                if not email or not password:
                    return JsonResponse({"success": False, "error": "The email address and password cannot be empty"}, status=400)

                user = authenticate(request, username=email, password=password)
                if user is not None:
                    login(request, user)
                    #next_url = request.POST.get('next') or request.GET.get('next') or '/'
                    return JsonResponse({"success": True, "message": "Login Successfully", "redirect_url": next_url})
                else:
                    return JsonResponse({"success": False, "error": "Incorrect Email or Password"}, status=401)
            except json.JSONDecodeError:
                logger.error("Invalid JSON data in login request body.")
                return JsonResponse({"success": False, "error": "Invalid JSON data"}, status=400)
            except AttributeError:
                return JsonResponse({"success": False, "error": "The request body is empty"}, status=400)
            except Exception as e:  # Capture other possible exceptions
                logger.error("An unexpected error occurred in AJAX login view: %s", e, exc_info=True)
                return JsonResponse({"success": False, "error": str(e)}, status=500)
        else:
            # Form Login Processing (HTML)
            email = request.POST.get("username") or request.POST.get("email")
            password = request.POST.get("password")
            next_url = request.GET.get('next') or request.POST.get('next') or '/'

            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next') or request.POST.get('next') or '/'
                return redirect(next_url)
            else:
                return render(request, 'login.html', {
                    'error': 'Invalid credentials',
                    'next': next_url
                })

#User settings page
@login_required
def user_settings_view(request):
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return render(request, 'Payroll_app/error.html', {'message': 'The current user has not bound the employee information'})

    approvals = SalaryAdjustmentApproval.objects.filter(employee=employee)
    pending_approvals = Approval.objects.filter(status='pending',
                                                employee=request.user.employee)
    api_key = APIKey.objects.filter(user=request.user).first()
    recent_activity = Log.objects.filter(user_email=request.user.email).order_by('-timestamp')[:10]
    # Prepare data for template rendering
    approvals_data = [{
        'id': a.id,
        'request_type': a.request_type,
        'employee_name': f"{a.employee.user.first_name} {a.employee.user.last_name}" if a.employee else "N/A",
        'submitted_at': timezone.localtime(a.submitted_at).strftime("%Y-%m-%d %H:%M"),
        'status': a.status
    } for a in pending_approvals]

    context = {
        'employee': employee,
        'approvals': approvals,
        'pending_approvals': pending_approvals,
        'api_key': api_key.key_string if api_key else None,
        'expires_at': api_key.expires_at if api_key else None,
        'recent_activity': recent_activity,
        'reject_approval_url_template': '/api/approvals/{approval_id}/reject/',
        'generate_api_key_url': reverse('generate_api_key_api'),
        'revoke_api_key_url': reverse('revoke_api_key_api'),
    }
    return render(request, 'Payroll_app/user_settings.html',context)

CustomUser = get_user_model()

@receiver(post_save, sender=CustomUser)
def create_employee_for_user(sender, instance, created, **kwargs):
    if not utils.GENERATING_DATA:
        if created and not hasattr(instance,'employee'):
            try:
                Employee.objects.create(user=instance, hire_date=timezone.now().date())  # Set hire_date to the current date
                print(f"Employee created for user: {instance.email}")  # testing
            except Exception as e:
                print(f"Error creating employee for user {instance.email}: {e}")# error handling

@login_required
@require_POST
def generate_api_key_api(request):
    try:
        user = request.user
        # Invalidate existing keys (optional, but a good practice)
        APIKey.objects.filter(user=user, is_active=True).update(is_active=False)

        # Generate a new secure API key
        raw_key = get_random_string(32)  # Generate a strong random key
        api_key = APIKey.objects.create(
            user=user,
            name=f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            key_hash="",  # Will be set by set_key
            salt="",  # Will be set by set_key
        )
        api_key.set_key(raw_key)
        api_key.save()

        return JsonResponse({'status': 'success', 'api_key': raw_key})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
def revoke_api_key_api(request):
    try:
        user = request.user
        APIKey.objects.filter(user=user, is_active=True).update(is_active=False)
        return JsonResponse({'status': 'success', 'message': 'API key revoked.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def get_pending_approvals(request):
    approvals = Approval.objects.filter(employee__user=request.user, status='pending').select_related('employee__user').order_by('submitted_at')
    data = [approval_to_dict(approval) for approval in approvals]  # Use serializer
    return api_response(data=data)

@login_required
@require_POST
def reject_approval_api(request, approval_id):
    try:
        approval = Approval.objects.get(pk=approval_id, status='pending')
        approval.status = 'rejected'
        approval.save()
        return JsonResponse({'status': 'success', 'message': 'Approval rejected successfully.'})
    except Approval.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Approval not found or already processed.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

#Logout page
def logout_view(request):
    logout(request)
    return redirect('/?show_login=true')

#Search page
def search_view(request):
    query = request.GET.get('q', '').strip()
    results=[]

    if query:
        employees = Employee.objects.filter(
            Q(first_name__icontains=query)|
            Q(last_name__icontains=query)|
            Q(email__icontains=query)
        )[:10]
        results = [{"name": f"{e.first_name} {e.last_name} ({e.email})"} for e in employees]

    return JsonResponse({'results': results})

#Dashbord page
def salary_trend(request):
    # Read data from the database
    df = pd.DataFrame(list(Employee.objects.all().values('name', 'salary')))
    df.plot(kind='bar', x='name', y='salary')
    plt.title('Salary Distribution')
    plt.savefig('salary_trend.png')
    with open('salary_trend.png', 'rb') as f:
        return HttpResponse(f.read(), content_type='image/png')

from django_ratelimit.decorators import ratelimit

@ratelimit(key='user',rate='5/m')
def dashboard_view(request):
    dashboard_data = get_dashboard_stats()
    context = {
        'total_payroll': dashboard_data['total_payroll'],
        'avg_net_salary': dashboard_data['avg_net_salary'],
        'total_bonuses': dashboard_data['total_bonuses'],
        'employee_count': dashboard_data['employee_count'],
        'active_employees': dashboard_data['active_employees'],
        'pending_adjustments': dashboard_data['pending_adjustments'],
        'overdue_reports': dashboard_data['overdue_reports'],
        'trend_chart': get_trend_chart(),
        'dept_chart': get_dept_distribution_chart(),
        'heatmap_chart': get_annual_heatmap(),
        'export_fields': ['first_name', 'last_name', 'email', 'department__dept_name', 'salary'],  # 示例导出字段
        'departments': Department.objects.all(),  # Sample department data
    }
    return render(request, 'dashboard.html', context)

@require_POST
def generate_dashboard_report(request):
    try:
        dashboard_data = get_dashboard_stats()  # Obtain the data required for the dashboard

        # Process the data as needed and generate reports
        pdf_file = generate_dashboard_pdf(dashboard_data)

        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="dashboard_report.pdf"'
        return response

    except Exception as e:
        print(f"Error generating dashboard report: {e}")
        return HttpResponse(json.dumps({'error': 'Failed to generate report'}), status=500, content_type="application/json")


@require_GET
def export_chart_pdf_view(request):
    employees = Employee.objects.all()
    df = pd.DataFrame(list(employees.values('first_name', 'last_name', 'salary')))
    df['name'] = df['first_name'] + ' ' + df['last_name']
    df = df[['name', 'salary']]
    chart_buf = generate_salary_trend_chart(df)
    return export_chart_as_pdf(chart_buf)

@require_POST
def payroll_action(request):
    action = request.POST.get('action')
    if action == 'generate':
        # Implement the logic for generating monthly reports
        messages.success(request, "Monthly report generated successfully.")
    elif action == 'export':
        # Implement the logic for exporting CSV
        return redirect('export_salary_csv')
    else:
        messages.error(request, "Invalid action.")
    return redirect('home')

@require_GET
def export_chart_pdf(request):
    return export_all_charts_pdf()

def employee_export_form(request):
    departments = Department.objects.all()
    export_fields = ['first_name', 'last_name', 'email', 'phone', 'department', 'position', 'salary', 'rank', 'grade']
    return render(request, 'employee_export.html', {
        'departments': departments,
        'export_fields': export_fields
    })
@require_http_methods(["GET", "POST"])
def export_salary_data(request):
    logging.info(f"Received salary export request. Method: {request.method}, Query params: {request.GET}")

    if request.method == 'GET':
        data_source = request.GET
    elif request.method == 'POST':
        data_source = request.POST
    else:
        return HttpResponseBadRequest("Method Not Allowed", status=405)

    format = data_source.get('format','csv')
    time_range = data_source.get('time_range')
    start_date_str = data_source.get('start_date')
    end_date_str = data_source.get('end_date')

    date_from = None
    date_to = None

    if time_range == 'custom':
        try:
            date_from = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            date_to = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid date format or missing dates for custom range: {e}")
            return HttpResponseBadRequest(
                "Invalid date format or missing dates for custom range. Please use YYYY-MM-DD for start_date and end_date.",
                content_type="text/plain")
    elif time_range == 'monthly':
        # Logic to get the start and end of the current month
        today = datetime.now().date()
        date_from = today.replace(day=1)
        import calendar
        date_to = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    elif time_range == 'yearly':
        # Logic to get the start and end of the current year
        today = datetime.now().date()
        date_from = today.replace(month=1, day=1)
        date_to = today.replace(month=12, day=31)
    try:
        response = generate_salary_export(date_from, date_to, format)
        logging.info(f"Successfully generated export with status: {format}")
        return response
    except Exception as e:
        logging.error(f"Error generating export: {e}", exc_info=True)
        return HttpResponse(f"Error generating export: {e}", status=500, content_type="text/plain")


def export_employees(request):
    if request.method == 'POST':
        format = request.POST.get('format')
        fields = request.POST.getlist('fields')
        departments = request.POST.getlist('departments')

        try:
            response = generate_employee_export(format, fields, departments)
            return response
        except Exception as e:
            return HttpResponse(f"Error generating export: {e}", status=500, content_type="text/plain")
    else:
        return HttpResponseBadRequest("Invalid request method", content_type="text/plain")


def generate_report(request):
    data = Payroll.objects.all()
    return render(request, 'report.html', {'payroll_data': data})

def export_payroll(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payroll.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee', 'Amount', 'Date'])

    for item in Payroll.objects.all():
        writer.writerow([item.employee.name, item.amount, item.date])
    return response

#Employees page
@login_required
def employee_list_view(request):
    dept_id = request.GET.get('department')
    departments = Department.objects.all()
    employees = Employee.objects.prefetch_related('photo')
    employee=None
    if hasattr(request.user, 'employee'):
        employee = request.user.employee

    if dept_id:
        employees = employees.filter(department__id=dept_id)

    context = {
        'employees': employees,
        'departments': departments,
        'selected_dept': int(dept_id) if dept_id else '',
        'employee': employee,  # Add the logged-in user's employee data to the context
    }
    return render(request, 'employee_list.html', context)
# create api
@csrf_exempt
def api_add_employee(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            department_id=data.get('department')
            department = Department.objects.get(id=department_id)

            employee = Employee.objects.create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                department=department,
                salary=data['salary'],
                hire_date=data['hire_date'],
            )

            return JsonResponse({'success': True, 'id': employee.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})
#Administrations page
def admin_view(request):
    return render(request, 'admin.html')

#Salary page
def salary_view(request):
    # Obtain all the employee information
    all_employees_sorted = Employee.objects.all().order_by('first_name', 'last_name')

    random_ids = request.session.get('random_employee_ids')

    if random_ids is None:
        random_employees = random.sample(list(all_employees_sorted), min(len(all_employees_sorted), 5))
        random_ids = [emp.id for emp in random_employees]
        request.session['random_employee_ids'] = random_ids
        employees = random_employees
    else:
        # If the session already exists, obtain the employee object by ID
        employees = Employee.objects.filter(id__in=random_ids).order_by('first_name', 'last_name')
    initial_employees = employees[:5]
    salary_logs = Log.objects.filter(model_name='Payroll').order_by('-timestamp')[:3]
    context = {
        'employees': initial_employees,
        'all_employees': all_employees_sorted[:5],  # Pass all employees for the template to iterate (initially hidden)
        'salary_logs': salary_logs,
    }
    return render(request, 'salary.html', context)

def search_employees(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'This endpoint only accepts GET requests.'}, status=405)
    query = request.GET.get('q', '').strip()

    try:
        if query:
            employees = Employee.objects.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).values('id', 'first_name', 'last_name')
            return JsonResponse(list(employees), safe=False)
        else:
            all_employees = list(Employee.objects.all().values('id', 'first_name', 'last_name'))
            if len(all_employees) > 6:
                random_employees = random.sample(all_employees, 6) #Randomly select 6 people
            else:
                random_employees = all_employees  # If there are less than 6 digits, all will be displayed
            return JsonResponse(random_employees, safe=False)
    except Exception as e:
        logging.error(f"Search error: {e}")
        return JsonResponse({'error': 'An error occurred during the search.'}, status=500)

#Obtain the employee selection and parameters passed from the front end
@csrf_exempt
@require_POST
def calculate_salary(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)# Parse the JSON data sent by the front end
            employee_ids=data.get('employee_ids')
            performance_coefficient = Decimal(str(data.get('performance',1.0))) # get performance coefficient
            allowance = Decimal(str(data.get('allowance', 0.0)))  # get allowances
            deduction = Decimal(str(data.get('deduction', 0.0)))  # get deductions
            # The basic salary is assumed to be 20,000
            if not employee_ids:
                return JsonResponse({'error': 'No employees selected'}, status=400)
            with transaction.atomic():
                employees = Employee.objects.filter(id__in=employee_ids)
                # Store the calculation results
                results = []
                for employee in employees:
                    basic_salary = employee.salary  # Or fetch from your Employee model if stored there
                    bonus = basic_salary * (performance_coefficient - 1)
                    total_salary = basic_salary + bonus + allowance - deduction
            #with connection.cursor() as cursor:
                #cursor.execute("SELECT optimize_tax(%s)",[total_salary])
                #optimal_tax=cursor.fetchone()[0]
                optimal_tax = total_salary * Decimal("0.10")
                net_salary=total_salary-optimal_tax

                # Save the result (adjust this based on your models)
                Payroll.objects.create(
                    employee=employee,
                    basic_salary=basic_salary,
                    bonus=bonus,
                    allowance=allowance,
                    deduction=deduction,
                    total_salary=total_salary,
                    tax_amount=optimal_tax,
                    pay_date=timezone.now().date(),
                )
                results.append({  # calculate total salary

                    'employee_name': f"{employee.first_name} {employee.last_name}",
                    'basic_salary': str(basic_salary),
                    'bonus': str(bonus),
                    'allowance': str(allowance),
                    'deduction': str(deduction),
                    'total_salary': str(total_salary),
                    'optimal_tax': str(optimal_tax),
                    'net_salary': str(net_salary),
                })

                # Add operation Log records
                Log.objects.create(
                    user_email=request.user.email if request.user.is_authenticated else 'unknown',
                    action='create',
                    model_name='Payroll',
                    object_id=employee.id,
                    timestamp=timezone.now(),
                    changes={
                        'employee': f"{employee.first_name} {employee.last_name}",
                        'total_salary': f'{total_salary:.2f}',
                        'performance': float(performance_coefficient),
                        'allowance': float(allowance),
                        'deduction': float(deduction),
                        'optimal_tax': f'{optimal_tax:.2f}',
                        'net_salary': f'{net_salary:.2f}',
                    },
                    log_type='operation'
                )
            return JsonResponse({'status': 'success', 'results': results})  # Return the JSON response
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})  # Handle exceptions and return error messages

def detect_salary_anomalies(request):
 # from payroll_system_db get data
    employees = Employee.objects.all().values('id', 'salary', 'bonus', 'performance')
    df = pd.DataFrame(list(employees))

    # Create and train the Isolation Forest model
    model = IsolationForest(contamination=0.01, random_state=42)
    model.fit(df[['salary', 'bonus', 'performance']])

    # Predicted outliers
    df['anomaly'] = model.predict(df[['salary', 'bonus', 'performance']])

    # Convert the result back to the format that Django can use
    anomalous_employee_ids = df[df['anomaly'] == -1].index.tolist()
    anomalous_employees = Employee.objects.filter(id__in=anomalous_employee_ids)
    return render(request, 'payroll/anomalies.html', {'anomalous_employees': anomalous_employees})

#Allowances & deductions page
def all_ded_view(request):
    departments = Department.objects.all()
    employee_ranks = Employee.RANK_CHOICES
    operation_logs = Log.objects.all().order_by('-timestamp')  # Fetch all logs, ordered by timestamp (newest first)
    context = {
        'departments': departments,
        'employee_ranks': employee_ranks,
        'operation_logs': operation_logs,
    }
    return render(request, 'all_ded.html', context)

def all_ded_data(request):
    # Allowance  data
    allowance_types = Allowance.ALLOWANCE_TYPES
    allowances = [
        {
            'name': label,
            'key': key,
            'default_amount': '25.00' if key == 'meal' else '0.45' if key == 'transportation' else '0.00'
        }
        for key, label in allowance_types
    ]

    deduction_types = Deduction.DEDUCTION_TYPES
    deductions = [
        {
            'name': label,
            'key': key,
            'default_amount': '20.00' if key == 'income_tax' else '13.25' if key == 'national_insurance' else '0.00'
        }
        for key, label in deduction_types
    ]

    # Condition type
    condition_types = [
        {'value': c[0], 'label': c[1]} for c in RuleConfig.CONDITION_TYPE_CHOICES
    ]

    # Calculation method
    calculation_types = [
        {'value': c[0], 'label': c[1]} for c in RuleConfig.CALCULATION_TYPE_CHOICES
    ]

    # All departments (for abnormal configuration)
    departments = [
        {'id': d.id, 'name': d.dept_name} for d in Department.objects.all()
    ]

    return JsonResponse({
        'allowances': allowances,
        'deductions': deductions,
        'condition_types': condition_types,
        'calculation_types': calculation_types,
        'departments': departments,
    })

@csrf_exempt
def api_import_employees_csv(request):  # CHANGE 5:  View function for CSV import
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            csv_data = data['csv_data']
            csv_file = csv.reader(csv_data.splitlines())
            header = next(csv_file)  # Skip header row (assuming there is one)

            for row in csv_file:
                # Assuming CSV structure matches your Employee model
                # Adjust this part based on your CSV's column order
                first_name = row[0]
                last_name = row[1]
                email = row[2]
                department_name = row[3]
                salary = float(row[4])
                hire_date = row[5]

                department = Department.objects.get(dept_name=department_name)  # Get Department instance
                Employee.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    department=department,
                    salary=salary,
                    hire_date=hire_date
                )

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid method'})

def is_admin(user):
    return user.role == CustomUser.ADMIN

#Get linked history
def api_get_employee_history(request):
    try:
        history = list(Log.objects.all().values())  # Get all history records
        return JsonResponse({'success': True, 'history': history})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_admin)
def configure_rule(request):
    #Debugging
    print(f"configure_rule view: User is authenticated: {request.user.is_authenticated}")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Create rule configuration
            rule = RuleConfig.objects.create(
                name=data.get('rule_name'),
                condition_type=data.get('condition_type'),
                comparator=data.get('comparator'),
                threshold=data.get('threshold'),
                calculation_type=data.get('calculation_type'),
                value=data.get('value'),
                created_by=request.user
            )

            # Handling and exclusion department
            exclude_dept_ids = data.get('exclude_departments',[])
            if not isinstance(exclude_dept_ids, list):
                exclude_dept_ids = [exclude_dept_ids]
            rule.exclude_departments.set(exclude_dept_ids)

            filtered_employees = Employee.objects.filter(department='Sales', level__gt=5)
            # Log record
            Log.objects.create(
                user_email=request.user.email,
                action='execute',
                model_name='RuleConfig',
                object_id=rule.id,
                changes={'affected_employees': filtered_employees.count()},
                timestamp=timezone.now(),
                log_type='system'
            )
            return JsonResponse({'status': 'success', 'rule_id': rule.id})
        except Exception as e:
            print(f"Error creating rule: {e}")  # Log the error on the server
            return JsonResponse({'status': 'error', 'message': str(e)})
    else:
        # The GET request returns option data
        departments = Department.objects.values('id', 'dept_name')
        return JsonResponse({
            'departments': list(departments),
            'employee_ranks': Employee.RANK_CHOICES,
            'grades': Employee.GRADE_CHOICES
        })

@require_POST
@login_required #  Protect this view
def execute_rule(request):
    try:
        data = json.loads(request.body)
        rank = data.get('rank')
        comparator = data.get('comparator')
        calc_mode = data.get('calcMode')
        calc_value = data.get('calcValue')
        exceptions = data.get('exceptions', [])

        #  Validation (Example)
        if not all([rank, comparator, calc_mode, calc_value]):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
        try:
            calc_value = Decimal(calc_value)
        except:
            return JsonResponse({'status': 'error', 'message': 'Invalid calculation value'})

        #  1. Fetch Employees
        employees = Employee.objects.all()
        if comparator == '>':
            employees = employees.filter(rank__gt=rank)
        elif comparator == '<':
            employees = employees.filter(rank__lt=rank)
        elif comparator == '==':
            employees = employees.filter(rank=rank)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid comparator'})

        employees = employees.exclude(department_id__in=exceptions)
        filtered_employees = employees

        #  2. Calculate Adjustment and Create Records
        for employee in filtered_employees:
            if calc_mode == 'percent':
                adjustment = employee.salary * (calc_value / 100)
            elif calc_mode == 'fixed':
                adjustment = calc_value
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid calculation mode'})

            #  Create Allowance/Deduction (Example -  Allowance)
            Allowance.objects.create(
                employee=employee,
                allowance_type='Rule-Based Adjustment',
                amount=adjustment,
                effective_date=timezone.now().date()
            )

            #  3. Log the action
            Log.objects.create(
                user_email=request.user.email,
                action='Rule Executed',
                model_name='Allowance',  #  Or 'Deduction'
                object_id=Allowance.objects.last().id,
                changes={
                    'employee': employee.id,
                    'adjustment': adjustment
                }
            )

        return JsonResponse({'status': 'success', 'message': 'Rule executed', 'affected': len(filtered_employees)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def create_allowance(request):
    try:
        # Assuming you're getting allowance data from a POST request
        data = json.loads(request.body)  # Parse JSON data
        allowance_type = data.get('allowance_type')
        amount = data.get('amount')
        employee_id = data.get('employee_id') # Get employee ID
        effective_date = data.get('effective_date')

        # ... Validation (add proper validation!) ...

        allowance = Allowance.objects.create(
            allowance_type=allowance_type,
            amount=amount,
            employee_id=employee_id,
            effective_date=effective_date
        )

        Log.objects.create(
            user_email=request.user.email,
            action='create',
            model_name='Allowance',
            object_id=allowance.id,
            changes={
                'allowance_type': allowance_type,
                'amount': amount,  # Convert Decimal to string for serialization
                'employee_id': employee_id,
                'effective_date': effective_date,
            },
            timestamp=timezone.now(),
            log_type='operation' # Ensure log_type is set
        )

        return JsonResponse({'status': 'success', 'message': 'Allowance created'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def update_allowance(request, allowance_id):
    try:
        data = json.loads(request.body)
        allowance = Allowance.objects.get(pk=allowance_id)

        changes = {}  # Dictionary to store changes
        if 'allowance_type' in data and data['allowance_type'] != allowance.allowance_type:
            changes['old_allowance_type'] = allowance.allowance_type
            changes['new_allowance_type'] = data['allowance_type']
            allowance.allowance_type = data['allowance_type']

        if 'effective_date' in data and data['effective_date'] != str(allowance.effective_date):
            changes['old_effective_date'] = str(allowance.effective_date)
            changes['new_effective_date'] = data['effective_date']
            allowance.effective_date = data['effective_date']

        if 'amount' in data and data['amount'] != str(allowance.amount):
            changes['old_amount'] = allowance.amount  # <--- POTENTIAL ISSUE
            changes['new_amount'] = data['amount']  # <--- POTENTIAL ISSUE
            allowance.amount = data['amount']

        return JsonResponse({'status': 'success', 'message': 'Allowance updated'})
    except Allowance.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Allowance not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def delete_allowance(request, allowance_id):
    try:
        allowance = Allowance.objects.get(pk=allowance_id)
        allowance_type = allowance.allowance_type  # Store for logging
        amount = allowance.amount
        employee_id = allowance.employee_id
        effective_date = allowance.effective_date

        allowance.delete()

        Log.objects.create(
            user_email=request.user.email,
            action='delete',
            model_name='Allowance',
            object_id=allowance_id,  # Still have the ID even after deletion
            changes={
                'allowance_type': allowance_type,
                'amount': amount,
                'employee_id': employee_id,
                'effective_date': str(effective_date),
            },
            timestamp=timezone.now(),
            log_type='operation'
        )
        return JsonResponse({'status': 'success', 'message': 'Allowance deleted'})

    except Allowance.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Allowance not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def log_view(request):
    # Query the operation log
    operation_logs = Log.objects.filter(log_type='operation')

    # Query the system log
    system_logs = Log.objects.filter(log_type='system')

    # Pass the log data to the template
    return render(request, 'log.html', {
        'operation_logs': operation_logs,
        'system_logs': system_logs,
    })

def error_view(request):
    return render(request, 'Payroll_app/error.html')