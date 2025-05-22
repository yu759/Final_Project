import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from Payroll_app.models import Department, Employee


class Command(BaseCommand):
    help = 'Creates a default superuser if not exists'

    def handle(self, *args, **options):
        CustomUser = get_user_model()
        admin_email = 'admin@example.com'
        if not CustomUser.objects.filter(email=admin_email).exists():
            admin_user=CustomUser.objects.create_superuser(
                email='admin@example.com',
                password='AU250201',
                first_name='Admin',
                last_name='User',
                role=CustomUser.ADMIN
            )
            self.stdout.write(self.style.SUCCESS('Successfully created default admin user.'))

            department= Department.objects.first()
            employee = Employee.objects.create(
                user=admin_user,
                first_name='Admin',
                last_name='User',
                email=admin_email,
                department=department,
                salary=0,
            )
            self.stdout.write(self.style.SUCCESS(' Created and bound Employee to admin user'))
        else:
            self.stdout.write(self.style.SUCCESS('Default admin user already exists.'))