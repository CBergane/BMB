from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url
from django.views.decorators.cache import never_cache


def owner_required(view_func):
    """Allow only authenticated, active superusers into owner views."""

    @wraps(view_func)
    def protected_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                resolve_url(settings.LOGIN_URL),
            )

        if not user.is_active or not user.is_superuser:
            raise PermissionDenied

        response = view_func(request, *args, **kwargs)
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response

    return never_cache(protected_view)
