from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from Payroll_app.models import Employee, Log, CustomUser
from django.db import IntegrityError
from Payroll_app import utils

@receiver(post_save, sender=Employee)
def create_user_for_employee(sender, instance, created, **kwargs):
    if not utils.GENERATING_DATA:
        if created and not instance.user:
            password = instance.generate_password()
            base_email = f"{instance.first_name.lower()}.{instance.last_name.lower()}@company.com"
            email = base_email
            suffix = 1
            while True:
                try:
                    user = CustomUser.objects.create_user(
                        email=email,
                        password=password,
                        role=CustomUser.USER
                    )
                    instance.user = user
                    instance.save()
                    break  # successfully, Exit the loop
                except IntegrityError:
                    email = f"{base_email.split('@')[0]}{suffix}@{base_email.split('@')[1]}"
                    suffix += 1

@receiver(post_save, sender=Employee)
def log_employee_save(sender, instance, created, **kwargs):
    Log.objects.create(
        user_email="system@auto.log",  # 或用 request.user.email if available
        action='create' if created else 'update',
        model_name='Employee',
        object_id=instance.id,
        changes={"first_name": instance.first_name, "last_name": instance.last_name}
    )

@receiver(post_delete, sender=Employee)
def log_employee_delete(sender, instance, **kwargs):
    Log.objects.create(
        user_email="system@auto.log",
        action='delete',
        model_name='Employee',
        object_id=instance.id,
        changes={"first_name": instance.first_name, "last_name": instance.last_name}
    )
