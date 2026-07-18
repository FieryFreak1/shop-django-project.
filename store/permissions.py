# store/permissions.py
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Product


def dashboard_permission(permission_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(
                request.user,
                "admin_profile",
                None
            )

            if not profile:
                raise PermissionDenied

            if not profile.is_active:
                raise PermissionDenied

            if not getattr(profile, permission_name, False):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def partner_update_stock(request, product_id):
    # Superuser может редактировать любой товар
    if request.user.is_superuser:
        return get_object_or_404(
            Product,
            id=product_id
        )

    # Партнёр может редактировать только свой товар
    partner_profile = getattr(
        request.user,
        "partner_profile",
        None
    )

    if partner_profile and partner_profile.is_active:
        return get_object_or_404(
            Product,
            id=product_id,
            owner=request.user
        )

    # Обычный администратор — любой товар
    admin_profile = getattr(
        request.user,
        "admin_profile",
        None
    )

    if admin_profile and admin_profile.is_active:
        return get_object_or_404(
            Product,
            id=product_id
        )

    raise PermissionDenied(
        "У вас нет прав для редактирования товара."
    )