from django.urls import path
from Payroll_app import views
from Payroll_app.views import export_chart_pdf_view, export_chart_pdf, export_employees, \
    employee_export_form
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    #dashboard
    path('', views.dashboard_view, name='home'), # home page
    path('export/pdf/', export_chart_pdf_view, name='export_chart_pdf'),
    path('export/chart/pdf/', export_chart_pdf, name='export_chart_pdf'),
    path('export/salary/', views.export_salary_data, name='export_salary_data'),
    path('export/employees/', export_employees, name='export_employees'),
    path('export/form/', employee_export_form, name='employee_export_form'),
    path('generate_dashboard_report/', views.generate_dashboard_report, name='generate_dashboard_report'),

    #login,logout,settings
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('Payroll_app/user_settings/', views.user_settings_view, name='user_settings'),
    path('api/approvals/<int:approval_id>/reject/', views.reject_approval_api, name='reject_approval_api'),
    path('api/generate_api_key/', views.generate_api_key_api, name='generate_api_key_api'),
    path('api/revoke_api_key/', views.revoke_api_key_api, name='revoke_api_key_api'),
    path('Payroll_app/error/', views.error_view, name='error'),
    path('logout/', views.logout_view, name='logout'),

    #admin
    path('admin/', views.admin_view, name='admin'),
    path('admin/add_new_user_form/', views.register_employee, name='add'),

    #search
    path('search/', views.search_view, name='search'),

    #employee
    path('employee_list/', views.employee_list_view, name='employee_list'),
    path('api/employees/add/', views.api_add_employee, name='api_add_employee'),
    path('api/employees/import/', views.api_import_employees_csv, name='api_import_csv'),
    path('api/employees/history/', views.api_get_employee_history, name='api_get_employee_history'),

    #salary
    path('salary/', views.salary_view, name='salary'),
    path('calculate_salary/', views.calculate_salary, name='calculate_salary'),
    path('payroll/anomalies/', views.detect_salary_anomalies, name='anomalies'),
    #search_salary
    path('employees/search/', views.search_employees, name='search_employees'),

    #allowances & Deductions
    path('all_ded/', views.all_ded_view, name='all_ded'),
    path('api/all_ded_data/', views.all_ded_data, name='all_ded_data'),
    path('log/', views.log_view, name='log'),
    path('payroll/payroll_action/', views.payroll_action, name='payroll_action'),
    path('configure-rule/', views.configure_rule, name='configure_rule'),
    path('execute-rule/', views.execute_rule, name='execute_rule'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)