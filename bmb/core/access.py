from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url
from django.utils.cache import patch_cache_control
from django.views.decorators.cache import never_cache


def active_account_required(view_func):
    """Require an authenticated, active user and protect private account data."""

    @wraps(view_func)
    def protected_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                resolve_url(settings.LOGIN_URL),
            )

        if not user.is_active:
            raise PermissionDenied

        response = view_func(request, *args, **kwargs)
        patch_cache_control(response, private=True)
        return response

    return never_cache(protected_view)
