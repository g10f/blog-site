from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware


# from https://github.com/cfpb/consumerfinance.gov/blob/main/cfgov/core/middleware.py
class PathBasedCsrfViewMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        csrf_required_paths = getattr(settings, "CSRF_REQUIRED_PATHS", None)

        # If CSRF_REQUIRED_PATHS is not configured, apply the CSRF middleware
        # to everything. Otherwise only apply it if the request path matches
        # the configured paths.
        if csrf_required_paths is not None and not any(request.path.startswith(path) for path in csrf_required_paths):
            return None

        return super().process_view(request, callback, callback_args, callback_kwargs)
