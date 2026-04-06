from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from .models import Permission, User, UserPermission, db


def load_current_user():
    user_id = session.get("user_id")
    if not user_id:
        g.user = None
        g.permission_keys = set()
        return
    g.user = db.session.get(User, user_id)
    if g.user is None:
        g.permission_keys = set()
        return

    permission_rows = (
        UserPermission.query.join(Permission, Permission.id == UserPermission.permission_id)
        .filter(UserPermission.user_id == g.user.id)
        .all()
    )
    g.permission_keys = {row.permission.key for row in permission_rows}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.get("user") is None:
            flash("Faca login para continuar.", "warning")
            return redirect(url_for("main.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user = g.get("user")
            if user is None:
                flash("Faca login para continuar.", "warning")
                return redirect(url_for("main.login", next=request.path))
            if user.role not in roles:
                flash("Voce nao tem permissao para esta operacao.", "danger")
                return redirect(url_for("main.dashboard"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def permission_required(permission_key: str):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user = g.get("user")
            if user is None:
                flash("Faca login para continuar.", "warning")
                return redirect(url_for("main.login", next=request.path))

            user_permissions = g.get("permission_keys", set())
            if permission_key not in user_permissions:
                flash("Voce nao tem permissao para esta operacao.", "danger")
                return redirect(url_for("main.dashboard"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def current_user_can(permission_key: str):
    return permission_key in g.get("permission_keys", set())
