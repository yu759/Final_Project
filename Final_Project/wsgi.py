import os
from django.core.wsgi import get_wsgi_application

# It must match the actual path of the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Final_Project.settings')

# Make sure the variable names are correct
application = get_wsgi_application()