import os
import django
from faker import Faker
from django.core.management.base import BaseCommand
from Payroll_app.models import Employee, EmployeePhoto
from django.core.files.images import ImageFile
import requests
from io import BytesIO
import time
import random
from PIL import Image, ImageDraw

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Final_Project.settings')
django.setup()


class Command(BaseCommand):
    help = "Generate fake employee photos for existing employees"

    def handle(self, *args, **kwargs):
        fake = Faker()
        employees = Employee.objects.all()
        num_employees = employees.count()

        self.stdout.write(self.style.SUCCESS(f"Found {num_employees} existing employees."))

        def create_fallback_image(employee_id):
            """Generates a simple fallback image with the employee ID."""
            img = Image.new('RGB', (100, 100), color='lightgray')
            d = ImageDraw.Draw(img)
            d.text((50, 50), str(employee_id), fill=(0, 0, 0))
            buffer = BytesIO()
            img.save(buffer, 'jpeg')
            buffer.seek(0)
            return ImageFile(buffer, name=f"fallback_photo_{employee_id}.jpg")

        def check_image_service_availability(url):
            """Checks if a given image service URL is responding."""
            try:
                requests.head(url, timeout=5)
                return True
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Image service check failed for {url}: {e}"))
                return False

        # Define reliable image sources (you might need to find better ones)
        reliable_image_sources = [
            "https://i.pravatar.cc/{width}?u={employee_id}",  # Decent, but limited styles
            "https://picsum.photos/{width}/{height}/?random",  # More general, but sometimes has people
            # Add more reliable sources here if you find them
        ]

        def get_reliable_image_url(employee_id, width=100, height=100):
            """Attempts to get a reliable image URL, prioritizing human faces."""
            random.shuffle(reliable_image_sources)  # Randomize source order

            for source in reliable_image_sources:
                url = source.format(width=width, height=height, employee_id=employee_id)
                if check_image_service_availability(url):
                    return url
            return None  # No reliable source found

        for employee in employees:
            if not hasattr(employee, 'photo'):
                max_retries = 3
                retry_delay = 5
                use_fallback = False

                image_url = get_reliable_image_url(employee.id)

                if image_url:
                    for attempt in range(max_retries):
                        try:
                            response = requests.get(image_url, stream=True, timeout=10)
                            response.raise_for_status()

                            image_name = f"fake_photo_{employee.id}.jpg"
                            image_file = ImageFile(BytesIO(response.content), name=image_name)

                            EmployeePhoto.objects.create(employee=employee, image=image_file)
                            self.stdout.write(
                                self.style.SUCCESS(f"Successfully created photo from URL for employee: {employee}"))
                            break

                        except requests.exceptions.RequestException as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error downloading image for employee {employee} (Attempt {attempt + 1}): {e}"))
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                            else:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"Failed to download image for employee {employee} after {max_retries} attempts. Using fallback."))
                                use_fallback = True
                                break

                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error creating photo object for employee {employee}: {e}"))
                            break
                else:
                    self.stdout.write(self.style.ERROR(f"No reliable image source available for employee: {employee}. Using fallback."))
                    use_fallback = True

                if use_fallback:
                    try:
                        fallback_image = create_fallback_image(employee.id)
                        EmployeePhoto.objects.create(employee=employee, image=fallback_image)
                        self.stdout.write(
                            self.style.WARNING(f"Created fallback photo for employee: {employee}"))
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error creating fallback photo for employee {employee}: {e}"))

            else:
                self.stdout.write(self.style.WARNING(f"Employee {employee} already has a photo. Skipping."))

        self.stdout.write(self.style.SUCCESS("Finished generating fake employee photos."))