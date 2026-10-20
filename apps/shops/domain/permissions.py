from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "OWNER"
    ATTENDANT = "ATTENDANT"


class Permission(str, Enum):
    CREATE_SHOP = "create_shop"
    CLOSE_SHOP = "close_shop"
    INVITE_STAFF = "invite_staff"
    DEACTIVATE_STAFF = "deactivate_staff"
    MANAGE_PRODUCTS = "manage_products"
    RECEIVE_STOCK = "receive_stock"
    ADJUST_STOCK = "adjust_stock"
    VIEW_REPORTS = "view_reports"
    MANAGE_SETTINGS = "manage_settings"
    SYNC_PUSH = "sync_push"
    SYNC_PULL = "sync_pull"
    RESOLVE_CONFLICTS = "resolve_conflicts"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OWNER: {
        Permission.CREATE_SHOP,
        Permission.CLOSE_SHOP,
        Permission.INVITE_STAFF,
        Permission.DEACTIVATE_STAFF,
        Permission.MANAGE_PRODUCTS,
        Permission.RECEIVE_STOCK,
        Permission.ADJUST_STOCK,
        Permission.VIEW_REPORTS,
        Permission.MANAGE_SETTINGS,
        Permission.SYNC_PUSH,
        Permission.SYNC_PULL,
        Permission.RESOLVE_CONFLICTS,
    },
    Role.ATTENDANT: {
        Permission.MANAGE_PRODUCTS,
        Permission.RECEIVE_STOCK,
        Permission.ADJUST_STOCK,
        Permission.SYNC_PUSH,
        Permission.SYNC_PULL,
    },
}


def get_permissions_for_role(role: Role) -> set[Permission]:
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def export_permissions_json() -> dict[str, list[str]]:
    return {role.value: sorted(p.value for p in perms) for role, perms in ROLE_PERMISSIONS.items()}
