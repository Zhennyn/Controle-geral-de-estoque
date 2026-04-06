from sqlalchemy import text

from .models import AuditLog, Permission, User, UserPermission, db


PERMISSION_DEFINITIONS = [
    ("view_dashboard", "Ver dashboard"),
    ("manage_products", "Gerenciar produtos"),
    ("manage_categories", "Gerenciar categorias"),
    ("manage_suppliers", "Gerenciar fornecedores"),
    ("manage_customers", "Gerenciar clientes"),
    ("manage_purchases", "Gerenciar compras"),
    ("manage_sales", "Gerenciar vendas"),
    ("manage_batches", "Gerenciar lotes"),
    ("manage_movements", "Gerenciar movimentacoes"),
    ("view_reports", "Ver relatorios"),
    ("manage_users", "Gerenciar usuarios"),
    ("manage_permissions", "Gerenciar permissoes"),
    ("manage_system", "Gerenciar sistema"),
    ("view_audit", "Ver auditoria"),
    ("import_products", "Importar produtos"),
    ("view_financial", "Ver financeiro"),
    ("manage_financial", "Gerenciar financeiro"),
    ("view_replenishment", "Ver reposicao inteligente"),
]

ROLE_DEFAULTS = {
    "admin": [key for key, _ in PERMISSION_DEFINITIONS],
    "operador": [
        "view_dashboard",
        "manage_products",
        "manage_customers",
        "manage_purchases",
        "manage_sales",
        "manage_batches",
        "manage_movements",
        "view_reports",
        "view_replenishment",
    ],
}


def ensure_permissions_seed():
    existing = {p.key: p for p in Permission.query.all()}
    for key, label in PERMISSION_DEFINITIONS:
        if key not in existing:
            db.session.add(Permission(key=key, label=label))

    db.session.flush()

    permissions = {p.key: p.id for p in Permission.query.all()}
    users = User.query.all()
    for user in users:
        user_permission_rows = (
            UserPermission.query.join(Permission, Permission.id == UserPermission.permission_id)
            .filter(UserPermission.user_id == user.id)
            .all()
        )
        existing_user_keys = {row.permission.key for row in user_permission_rows}
        for key in ROLE_DEFAULTS.get(user.role, []):
            if key in permissions and key not in existing_user_keys:
                db.session.add(UserPermission(user_id=user.id, permission_id=permissions[key]))

    db.session.commit()


def set_user_permissions(user_id: int, permission_keys: list[str]):
    UserPermission.query.filter_by(user_id=user_id).delete()
    permission_map = {p.key: p.id for p in Permission.query.all()}
    for key in permission_keys:
        if key in permission_map:
            db.session.add(UserPermission(user_id=user_id, permission_id=permission_map[key]))
    db.session.commit()


def assign_default_permissions_for_user(user_id: int, role: str):
    permission_map = {p.key: p.id for p in Permission.query.all()}
    for key in ROLE_DEFAULTS.get(role, []):
        if key in permission_map:
            db.session.add(UserPermission(user_id=user_id, permission_id=permission_map[key]))
    db.session.commit()


def ensure_phase2_schema():
    columns = {
        row[1] for row in db.session.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
    }
    if "entity_type" not in columns:
        db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN entity_type VARCHAR(80)"))
    if "entity_id" not in columns:
        db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN entity_id INTEGER"))
    db.session.commit()


def audit_log(
    username,
    action,
    endpoint=None,
    path=None,
    method=None,
    status_code=None,
    detail=None,
    entity_type=None,
    entity_id=None,
):
    log = AuditLog(
        username=username,
        action=action,
        endpoint=endpoint,
        path=path,
        method=method,
        status_code=status_code,
        detail=detail,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.session.add(log)
    db.session.commit()
