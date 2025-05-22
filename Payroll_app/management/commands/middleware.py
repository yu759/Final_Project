from django.core.cache import caches

class MyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache = caches['default']

    def __call__(self, request):
        # Cache-related logic...
        return self.get_response(request)