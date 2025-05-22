from django import forms
from django.contrib.auth.forms import AuthenticationForm
from Payroll_app.models import Employee, Department, Position


class LoginForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100,required=True)
    password = forms.CharField(label='Password', widget=forms.PasswordInput,required=True)

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")

class EmployeeRegistrationForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        exclude = ['user']

class EmployeeAdminRegisterForm(forms.Form):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=50)
    last_name = forms.CharField(required=True, max_length=50)
    hire_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    salary = forms.DecimalField(required=True)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    position = forms.ModelChoiceField(queryset=Position.objects.all(), required=True)
    rank = forms.CharField(required=False)
    grade = forms.CharField(required=False)

class AdminRegisterForm(forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField()
    last_name = forms.CharField()
    hire_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    position = forms.ModelChoiceField(queryset=Position.objects.all())