from django.contrib.admin.apps import AppConfig
from django.contrib.auth import get_user_model
import logging

class PayrollAppConfig(AppConfig):
    name = 'Payroll_app'

    def ready(self, employee=None):
        from django.db.utils import OperationalError
        try:
            CustomUser = get_user_model()
            if not CustomUser.objects.filter(email='admin@example.com').exists():
                CustomUser.objects.create_superuser(
                    email='admin@example.com',
                    password='AU250201',
                    first_name='Admin',
                    last_name='User',
                    is_staff=True,
                    is_superuser=True
                )

                logging.info("Default admin user created.")
        except OperationalError as e:
            logging.warning("Database not ready, skipped admin creation.")
        except Exception as e:
            logging.error(f"Error creating admin user: {e}")