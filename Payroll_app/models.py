import secrets
import bcrypt
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.core.cache import caches
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import JSONField

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    ADMIN = 'admin'
    USER = 'user'
    ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (USER, 'Regular User'),
    ]

    username = None  # Disable username field
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects=CustomUserManager()

class Department(models.Model):
    dept_name = models.CharField(max_length=100, unique=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.dept_name


class Position(models.Model):
    title = models.CharField(max_length=100)
    permissions = JSONField(null=True, blank=True)

    def __str__(self):
        return self.title

User = get_user_model()

class Employee(models.Model):
    RANK_CHOICES = [
        ('junior', 'Junior'),
        ('mid', 'Mid-Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
    ]

    GRADE_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='employee',null=True,blank=True)
    first_name = models.CharField(default='', max_length=50)
    last_name = models.CharField(default='', max_length=50)
    email = models.EmailField(default='', max_length=254, blank=False, null=False)
    phone = models.CharField(default='', max_length=20, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    exit_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(default='0.00', max_digits=10, decimal_places=2,null=True, blank=True)
    performance = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True,editable=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.SET_NULL)
    #new  field
    rank = models.CharField(max_length=10, choices=RANK_CHOICES, default='junior')
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES, default='C')

    def generate_password(self):
        if self.hire_date:
            date_part = self.hire_date.strftime("%y%m%d")
        else:
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for i in range(8))  # Generate an 8-digit random password

        first_initial = self.first_name[0].lower() if self.first_name else 'x'
        last_initial = self.last_name[0].lower() if self.last_name else 'x'
        return f"{first_initial}{last_initial}{date_part}".ljust(8, '0')[:8]

    def save(self,*args,**kwargs):
        self.is_active=self.exit_date is None
        super().save(*args,**kwargs)

    def get_cached_data(self):
        cache = caches['default']
        key = f'employee_{self.id}_data'
        data = cache.get(key)
        if not data:
            data = self.calculate_data()
            cache.set(key, data, 3600)
        return data

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class EmployeePhoto(models.Model):
    employee = models.OneToOneField('Employee', on_delete=models.CASCADE, related_name='photo')
    image = models.ImageField(upload_to='employee_photos/')  # You'll need Pillow installed
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.employee}"

class Bonus(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bonus_type = models.CharField(max_length=50)
    date_awarded = models.DateField()
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.bonus_type} - {self.amount}"

class Allowance(models.Model):
    ALLOWANCE_TYPES = [
        ('transportation', 'Transportation'),
        ('meal', 'Meal'),
        ('housing', 'Housing'),
        ('other', 'Other'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='allowances')
    allowance_type = models.CharField(max_length=50, choices=ALLOWANCE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()

    def __str__(self):
        return f"{self.allowance_type} - {self.amount} for {self.employee}"

class Deduction(models.Model):
    DEDUCTION_TYPES = [
        ('income_tax', 'Income Tax'),
        ('national_insurance', 'National Insurance'),
        ('retirement', 'Retirement Contribution'),
        ('loan', 'Loan Repayment'),
        ('other', 'Other'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='deductions')
    deduction_type = models.CharField(max_length=50, choices=DEDUCTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()

    def __str__(self):
        return f"{self.deduction_type} - {self.amount} for {self.employee}"


class Tax(models.Model):
    employee = models.ForeignKey(Employee, related_name='pensions',on_delete=models.CASCADE)
    income_tax = models.DecimalField(max_digits=10, decimal_places=2)
    national_insurance = models.DecimalField(max_digits=10, decimal_places=2)
    tax_year = models.IntegerField()

    def __str__(self):
        return f"Tax Year {self.tax_year} for {self.employee}"

class Pension(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    employer_contribution = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    employee_contribution = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    employer_contribution_percent = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                                        blank=True)
    employee_contribution_percent = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                                        blank=True)
    def __str__(self):
        return f"Pension for {self.employee}"

class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pension_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    pay_date = models.DateField()

    @property
    def net_salary(self):
        total_allowances = sum([a.amount for a in self.employee.allowances.all()])
        total_deductions = sum([d.amount for d in self.employee.deductions.all()])
        return self.basic_salary + self.bonus - self.tax_amount- total_deductions+ total_allowances

    def __str__(self):
        return f"Payroll {self.pay_date} for {self.employee}"

class Log(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    LOG_TYPE_CHOICES = [
        ('operation', 'Operation Log'),
        ('system', 'System Log'),
    ]
    user_email = models.EmailField()  # Operate the user
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = JSONField(null=True, blank=True)  # The field differences before and after the changes can be recorded

    log_type=models.CharField(max_length=20,choices=LOG_TYPE_CHOICES,default='operation')
    def __str__(self):
        return f"{self.timestamp} - {self.user_email} - {self.action} {self.model_name} {self.object_id}"
    class Meta:
        ordering=['-timestamp']

class RuleConfig(models.Model):
    CONDITION_TYPE_CHOICES = [
        ('rank', 'Employee Rank'),
        ('grade', 'Employee Grade'),
        ('department', 'Department')
    ]

    CALCULATION_TYPE_CHOICES = [
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ]

    name = models.CharField(max_length=100)
    condition_type = models.CharField(max_length=20, choices=CONDITION_TYPE_CHOICES)
    comparator = models.CharField(max_length=2)
    threshold = models.CharField(max_length=50)
    calculation_type = models.CharField(max_length=10, choices=CALCULATION_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    exclude_departments = models.ManyToManyField(Department, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"

    #User_settings
class Approval(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),  # Added 'cancelled'
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='approval_requests', null=True,
                                 blank=True)
    request_type = models.CharField(max_length=255)
    description = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Optional fields for generic approvals
    related_model = models.CharField(max_length=100, blank=True, null=True)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_approvals')
    modified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='modified_approvals')
    def __str__(self):
        return f"{self.request_type} - {self.employee.user.email} - {self.status}"

    def to_dict(self):
        data = {
            'id': self.id,
            'request_type': self.request_type,
            'description': self.description,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'status': self.status,
            'employee_id': self.employee.id if self.employee else None,
            'employee_name': self.employee.user.email if self.employee and self.employee.user else None,  # Use email
            'created_by': self.created_by.email if self.created_by else None,
            'modified_by': self.modified_by.email if self.modified_by else None,
            'related_model': self.related_model,
            'related_object_id': self.related_object_id,
        }
        return data

class ApprovalLog(models.Model):
    approval = models.ForeignKey(Approval, on_delete=models.CASCADE, related_name='status_log')
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models
    models.DateTimeField(auto_now_add=True)
    old_status = models.CharField(max_length=20, choices=Approval.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=Approval.STATUS_CHOICES)
    reason = models.TextField(blank=True, null=True)  # Optional reason for the change

    def __str__(self):
        return f"Approval {self.approval.id} status changed from {self.old_status} to {self.new_status} at {self.changed_at}"

    def to_dict(self):
        data = {
            'id': self.id,
            'approval_id': self.approval.approval_id,
            'changed_by': self.changed_by.email if self.changed_by else None,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'reason': self.reason,
        }
        return data

class APIKey(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, null=True)
    key_hash = models.CharField(max_length=255, unique=True)
    salt = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def set_key(self, raw_key):
        self.salt = bcrypt.gensalt().decode()  # Generate a new salt
        self.key_hash = bcrypt.hashpw(raw_key.encode(), self.salt.encode()).decode()

    def check_key(self, raw_key):
        return bcrypt.checkpw(raw_key.encode(), self.key_hash.encode())

    def __str__(self):
        return f"API Key for {self.user.email} ({self.name})"

    @classmethod
    def generate_key_string(cls):
        """Generates a secure, random API key string."""
        return secrets.token_urlsafe(32)

    def __str__(self):
        return f"API Key for {self.user.email} ({self.name})"

    def to_dict(self):
        data = {
            'id': self.id,
            'user_id': self.user.id,
            'user_email': self.user.email,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
        }
        return data

class SalaryAdjustmentApproval(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=100)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')])
