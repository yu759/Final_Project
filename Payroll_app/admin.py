import path
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.models import LogEntry
from django.contrib.admin import AdminSite
from django.core.checks import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from Payroll_app.forms import AdminRegisterForm
from Payroll_app.models import Employee, Department, Position, Payroll, Bonus, Pension, Tax, CustomUser
from django.http import HttpResponse
import csv

class CustomAdminSite(AdminSite):
    site_header = "Payroll Genius"
    site_title = "Payroll Admin Portal"
    index_title=" Welcome to use"

custom_admin_site = CustomAdminSite(name='custom_admin')

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )
    list_display = ('email', 'role', 'is_active')
    search_fields = ('email',)
    ordering = ('email',)

custom_admin_site.register(CustomUser, CustomUserAdmin)

from django.contrib.admin import SimpleListFilter
class ActiveStatusFilter(SimpleListFilter):
    title = 'On-the-job status'
    parameter_name = 'active_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Employed'),
            ('inactive', 'Have resigned'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(exit_date__isnull=True)
        if self.value() == 'inactive':
            return queryset.filter(exit_date__isnull=False)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'department', 'position', 'is_active']
    list_filter = ['department', 'position', ActiveStatusFilter]
    search_fields = ['first_name', 'last_name', 'email']

    add_form_template = "admin/add_new_user_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('admin/AddNewUser_form/', self.admin_site.admin_view(self.register_employee), name='employee-register'),
        ]
        return custom_urls + urls

    def register_view(self, request):
        if request.method == 'POST':
            form = AdminRegisterForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                user = CustomUser.objects.create_user(
                    email=data['email'],
                    password=['password'],
                    role=CustomUser.USER
                )
                employee = Employee.objects.create(
                    user=user,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    email=data['email'],
                    hire_date=data['hire_date'],
                    department=data['department'],
                    position=data['position'],
                )
                # 生成密码（举例用拼接）
                #pw = f"{data['first_name'][0].lower()}{data['last_name'].lower()}{data['hire_date'].strftime('%Y%m%d')}"
                #user.set_password(pw)
                #user.save()

                #send_mail(
                    #subject='Your account has been created',
                    #message=f'Hello {data["first_name"]}, your login password is: {pw}',
                    #from_email=settings.DEFAULT_FROM_EMAIL,
                    #recipient_list=[data['email']],
                #)
                messages.success(request, "User registered and email sent.")
                return redirect("..")
        else:
            form = AdminRegisterForm()
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title='Register Employee'
        )
        return TemplateResponse(request, "admin/add_new_user_form.html", context)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['dept_name', 'budget']
    search_fields = ['dept_name']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title']
    search_fields = ['title']

@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'bonus_type', 'date_awarded']
    list_filter = ['bonus_type', 'date_awarded']
    search_fields = ['employee__first_name', 'employee__last_name']

@admin.register(Pension)
class PensionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'employer_contribution', 'employee_contribution']
    search_fields = ['employee__first_name', 'employee__last_name']

@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ['employee', 'income_tax', 'national_insurance', 'tax_year']
    list_filter = ['tax_year']
    search_fields = ['employee__first_name', 'employee__last_name']


# 动态导出 Payroll 报表（HMRC 格式）
def export_payroll_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payroll_report.csv"'
    writer = csv.writer(response)

    # 表头
    writer.writerow(['Employee', 'Pay Date', 'Gross Pay', 'Tax', 'National Insurance', 'Pension', 'Net Salary'])

    # 数据行（根据 Payroll 模型中的计算字段）
    for obj in queryset:
        employee_name = f"{obj.employee.first_name} {obj.employee.last_name}"
        gross_pay = obj.basic_salary + obj.bonus
        net_salary = gross_pay - obj.tax_amount - obj.pension_amount
        writer.writerow([
            employee_name,
            obj.pay_date,
            gross_pay,
            obj.tax_amount,
            obj.tax.national_insurance if hasattr(obj, 'tax') else 'N/A',
            obj.pension_amount,
            net_salary
        ])
    return response

export_payroll_csv.short_description = "Export the selected salary record as an HMRC CSV report"

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    data_hierarchy='pay_date'
    list_display = ['employee', 'pay_date', 'basic_salary', 'bonus', 'tax_amount', 'net_salary']
    #list_filter = ['pay_date']
    search_fields = ['employee__first_name', 'employee__last_name']
    actions = [export_payroll_csv]

    def gross_pay(self,obj):
        return obj.basic_salary + obj.bonus
    gross_pay.short_description='Gross Pay'

 #Log management backend configuration
from Payroll_app.models import Log

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_email', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name', 'user_email')
    search_fields = ('user_email', 'model_name', 'object_id')
    readonly_fields = ('timestamp', 'user_email', 'action', 'model_name', 'object_id', 'changes')

    def has_add_permission(self, request):
        return False  # Manual addition is prohibited.

    def has_change_permission(self, request, obj=None):
        return False  # Editing is prohibited.

#Log management configuration
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['action_time', 'user', 'content_type', 'object_repr']
    list_filter = ['action_time']
    search_fields = ['user__email', 'object_repr']

custom_admin_site.register(LogEntry, LogEntryAdmin)