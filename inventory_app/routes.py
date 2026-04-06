from datetime import datetime, timezone
from datetime import date
import csv
from io import StringIO
import json

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from .auth import permission_required
from .backup_service import create_backup, list_backups, restore_backup
from .models import (
    AuditLog,
    Category,
    Customer,
    FinancialEntry,
    Permission,
    Product,
    ProductBatch,
    PurchaseOrder,
    PurchaseOrderItem,
    SalesOrder,
    SalesOrderItem,
    StockMovement,
    Supplier,
    User,
    UserPermission,
    db,
)
from .phase1_service import complete_sales_order, expiring_batches, receive_purchase_order
from .phase2_service import assign_default_permissions_for_user, audit_log, set_user_permissions
from .phase3_service import abc_and_replenishment, cashflow_last_days, financial_summary
from .services import StockError, create_movement, create_product, update_product
from .utils import csv_response

main_bp = Blueprint("main", __name__)


def _get_page_arg() -> int:
    raw = request.args.get("page", 1)
    try:
        return max(int(raw), 1)
    except (TypeError, ValueError):
        return 1


def _paginate(query, page: int, per_page: int):
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    has_prev = page > 1
    has_next = page * per_page < total
    return items, total, has_prev, has_next


def _parse_date_or_none(raw_value: str):
    value = (raw_value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _audit(action: str, detail: str | None = None, entity_type: str | None = None, entity_id=None):
    user = g.get("user")
    audit_log(
        username=user.username if user else None,
        action=action,
        endpoint=request.endpoint,
        path=request.path,
        method=request.method,
        status_code=200,
        detail=detail,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def _audit_changes(action: str, entity_type: str, entity_id, before: dict, after: dict):
    changes = {}
    for key in sorted(set(before.keys()) | set(after.keys())):
        if before.get(key) != after.get(key):
            changes[key] = {"before": before.get(key), "after": after.get(key)}

    if not changes:
        return

    detail = json.dumps(changes, ensure_ascii=True)
    # Mantem o tamanho de detalhe sob controle para o banco.
    if len(detail) > 245:
        detail = detail[:242] + "..."

    _audit(action, detail=detail, entity_type=entity_type, entity_id=entity_id)


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("user"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        next_url = request.form.get("next") or request.args.get("next")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, is_active=True).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            audit_log(
                username=user.username,
                action="auth:login",
                endpoint=request.endpoint,
                path=request.path,
                method=request.method,
                status_code=200,
            )
            flash("Login realizado com sucesso.", "success")
            return redirect(next_url or url_for("main.dashboard"))

        flash("Usuario ou senha invalidos.", "danger")

    return render_template("login.html", next_url=request.args.get("next", ""))


@main_bp.get("/logout")
def logout():
    session.clear()
    flash("Sessao encerrada.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/")
@permission_required("view_dashboard")
def dashboard():
    total_products = Product.query.count()
    total_items = db.session.query(func.coalesce(func.sum(Product.quantity), 0)).scalar()
    stock_value = db.session.query(
        func.coalesce(func.sum(Product.quantity * Product.cost_price), 0)
    ).scalar()
    low_stock_count = Product.query.filter(Product.quantity <= Product.min_stock).count()
    expiring_count = len(expiring_batches(30))
    pending_purchases = PurchaseOrder.query.filter_by(status="rascunho").count()
    pending_sales = SalesOrder.query.filter_by(status="rascunho").count()
    recent_movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(10).all()
    low_stock_products = (
        Product.query.filter(Product.quantity <= Product.min_stock)
        .order_by(Product.quantity.asc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_items=total_items,
        stock_value=stock_value,
        low_stock_count=low_stock_count,
        expiring_count=expiring_count,
        pending_purchases=pending_purchases,
        pending_sales=pending_sales,
        recent_movements=recent_movements,
        low_stock_products=low_stock_products,
    )


@main_bp.route("/clientes", methods=["GET", "POST"])
@permission_required("manage_customers")
def customers():
    if request.method == "POST":
        customer = Customer(
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            document=request.form.get("document", "").strip() or None,
        )

        if not customer.name:
            flash("Nome do cliente e obrigatorio.", "danger")
            return redirect(url_for("main.customers"))

        db.session.add(customer)
        db.session.commit()
        _audit("customer:create", detail=customer.name, entity_type="customer", entity_id=customer.id)
        flash("Cliente cadastrado com sucesso.", "success")
        return redirect(url_for("main.customers"))

    query = request.args.get("q", "").strip()
    customers_query = Customer.query
    if query:
        customers_query = customers_query.filter(
            Customer.name.ilike(f"%{query}%")
            | Customer.email.ilike(f"%{query}%")
            | Customer.phone.ilike(f"%{query}%")
            | Customer.document.ilike(f"%{query}%")
        )

    page = _get_page_arg()
    per_page = 20
    customers_list, total, has_prev, has_next = _paginate(
        customers_query.order_by(Customer.created_at.desc()), page, per_page
    )
    return render_template(
        "customers.html",
        customers=customers_list,
        query=query,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
    )


@main_bp.post("/clientes/<int:customer_id>/editar")
@permission_required("manage_customers")
def update_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Nome do cliente e obrigatorio.", "danger")
        return redirect(url_for("main.customers"))

    before = {
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "document": customer.document,
    }

    customer.name = name
    customer.email = request.form.get("email", "").strip() or None
    customer.phone = request.form.get("phone", "").strip() or None
    customer.document = request.form.get("document", "").strip() or None

    after = {
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "document": customer.document,
    }

    db.session.commit()
    _audit_changes("customer:update", "customer", customer.id, before, after)
    flash("Cliente atualizado com sucesso.", "success")
    return redirect(url_for("main.customers"))


@main_bp.post("/clientes/<int:customer_id>/deletar")
@permission_required("manage_customers")
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if customer.sales_orders:
        flash("Cliente possui vendas vinculadas e nao pode ser removido.", "danger")
        return redirect(url_for("main.customers"))

    db.session.delete(customer)
    db.session.commit()
    _audit("customer:delete", detail=customer.name, entity_type="customer", entity_id=customer_id)
    flash("Cliente removido com sucesso.", "warning")
    return redirect(url_for("main.customers"))


@main_bp.route("/compras", methods=["GET", "POST"])
@permission_required("manage_purchases")
def purchase_orders():
    if request.method == "POST":
        supplier_id = request.form.get("supplier_id", "")
        quick_supplier_name = request.form.get("quick_supplier_name", "").strip()
        if not supplier_id.isdigit() and not quick_supplier_name:
            flash("Selecione um fornecedor ou informe um novo fornecedor rapido.", "danger")
            return redirect(url_for("main.purchase_orders"))

        if not supplier_id.isdigit() and quick_supplier_name:
            supplier = Supplier(
                name=quick_supplier_name,
                email=request.form.get("quick_supplier_email", "").strip() or None,
                phone=request.form.get("quick_supplier_phone", "").strip() or None,
            )
            db.session.add(supplier)
            db.session.flush()
            supplier_id = str(supplier.id)

        expected_date_str = request.form.get("expected_date", "").strip()
        expected_date = None
        if expected_date_str:
            try:
                expected_date = datetime.strptime(expected_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Data prevista invalida.", "danger")
                return redirect(url_for("main.purchase_orders"))

        order = PurchaseOrder(
            supplier_id=int(supplier_id),
            notes=request.form.get("notes", "").strip() or None,
            expected_date=expected_date,
        )
        db.session.add(order)
        db.session.commit()
        _audit("purchase:create", entity_type="purchase_order", entity_id=order.id)
        flash(f"Pedido de compra #{order.id} criado.", "success")
        return redirect(url_for("main.purchase_order_detail", order_id=order.id))

    status = request.args.get("status", "").strip()
    supplier_filter = request.args.get("supplier_id", "").strip()
    start_date = _parse_date_or_none(request.args.get("start_date", ""))
    end_date = _parse_date_or_none(request.args.get("end_date", ""))

    orders_query = PurchaseOrder.query
    if status:
        orders_query = orders_query.filter(PurchaseOrder.status == status)
    if supplier_filter.isdigit():
        orders_query = orders_query.filter(PurchaseOrder.supplier_id == int(supplier_filter))
    if start_date:
        orders_query = orders_query.filter(PurchaseOrder.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        orders_query = orders_query.filter(PurchaseOrder.created_at <= datetime.combine(end_date, datetime.max.time()))

    page = _get_page_arg()
    per_page = 20
    orders, total, has_prev, has_next = _paginate(
        orders_query.order_by(PurchaseOrder.created_at.desc()), page, per_page
    )
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template(
        "purchase_orders.html",
        orders=orders,
        suppliers=suppliers,
        selected_status=status,
        selected_supplier=supplier_filter,
        selected_start_date=request.args.get("start_date", ""),
        selected_end_date=request.args.get("end_date", ""),
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
    )


@main_bp.route("/compras/<int:order_id>", methods=["GET", "POST"])
@permission_required("manage_purchases")
def purchase_order_detail(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)

    if request.method == "POST":
        if order.status != "rascunho":
            flash("Nao e possivel editar pedido ja recebido.", "danger")
            return redirect(url_for("main.purchase_order_detail", order_id=order.id))

        product_id = request.form.get("product_id", "")
        quantity = request.form.get("quantity", "")
        if not product_id.isdigit() or not quantity.isdigit() or int(quantity) <= 0:
            flash("Produto e quantidade validos sao obrigatorios.", "danger")
            return redirect(url_for("main.purchase_order_detail", order_id=order.id))

        expiry_date_str = request.form.get("expiry_date", "").strip()
        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Data de validade invalida.", "danger")
                return redirect(url_for("main.purchase_order_detail", order_id=order.id))

        item = PurchaseOrderItem(
            purchase_order_id=order.id,
            product_id=int(product_id),
            quantity=int(quantity),
            unit_cost=request.form.get("unit_cost", 0) or 0,
            lot_code=request.form.get("lot_code", "").strip() or None,
            expiry_date=expiry_date,
        )
        db.session.add(item)
        db.session.commit()
        _audit("purchase_item:create", entity_type="purchase_order", entity_id=order.id)
        flash("Item adicionado ao pedido de compra.", "success")
        return redirect(url_for("main.purchase_order_detail", order_id=order.id))

    products = Product.query.order_by(Product.name.asc()).all()
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template(
        "purchase_order_detail.html", order=order, products=products, suppliers=suppliers
    )


@main_bp.post("/compras/<int:order_id>/editar")
@permission_required("manage_purchases")
def update_purchase_order(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Nao e possivel editar pedido ja recebido.", "danger")
        return redirect(url_for("main.purchase_order_detail", order_id=order.id))

    before = {
        "supplier_id": order.supplier_id,
        "expected_date": order.expected_date.isoformat() if order.expected_date else None,
        "notes": order.notes,
    }

    supplier_id = request.form.get("supplier_id", "")
    if supplier_id.isdigit():
        order.supplier_id = int(supplier_id)

    expected_date = _parse_date_or_none(request.form.get("expected_date", ""))
    order.expected_date = expected_date
    order.notes = request.form.get("notes", "").strip() or None

    after = {
        "supplier_id": order.supplier_id,
        "expected_date": order.expected_date.isoformat() if order.expected_date else None,
        "notes": order.notes,
    }

    db.session.commit()
    _audit_changes("purchase:update", "purchase_order", order.id, before, after)
    flash("Pedido de compra atualizado.", "success")
    return redirect(url_for("main.purchase_order_detail", order_id=order.id))


@main_bp.post("/compras/<int:order_id>/itens/<int:item_id>/editar")
@permission_required("manage_purchases")
def update_purchase_item(order_id, item_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Nao e possivel editar itens de pedido ja recebido.", "danger")
        return redirect(url_for("main.purchase_order_detail", order_id=order.id))

    item = PurchaseOrderItem.query.filter_by(id=item_id, purchase_order_id=order.id).first_or_404()
    quantity = request.form.get("quantity", "")
    if not quantity.isdigit() or int(quantity) <= 0:
        flash("Quantidade invalida.", "danger")
        return redirect(url_for("main.purchase_order_detail", order_id=order.id))

    before = {
        "quantity": item.quantity,
        "unit_cost": float(item.unit_cost or 0),
        "lot_code": item.lot_code,
        "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
    }

    expiry_date = _parse_date_or_none(request.form.get("expiry_date", ""))
    item.quantity = int(quantity)
    item.unit_cost = request.form.get("unit_cost", 0) or 0
    item.lot_code = request.form.get("lot_code", "").strip() or None
    item.expiry_date = expiry_date

    after = {
        "quantity": item.quantity,
        "unit_cost": float(item.unit_cost or 0),
        "lot_code": item.lot_code,
        "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
    }

    db.session.commit()
    _audit_changes("purchase_item:update", "purchase_order_item", item.id, before, after)
    flash("Item de compra atualizado.", "success")
    return redirect(url_for("main.purchase_order_detail", order_id=order.id))


@main_bp.post("/compras/<int:order_id>/itens/<int:item_id>/deletar")
@permission_required("manage_purchases")
def delete_purchase_item(order_id, item_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Nao e possivel remover itens de pedido ja recebido.", "danger")
        return redirect(url_for("main.purchase_order_detail", order_id=order.id))

    item = PurchaseOrderItem.query.filter_by(id=item_id, purchase_order_id=order.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    _audit("purchase_item:delete", entity_type="purchase_order_item", entity_id=item_id)
    flash("Item removido do pedido de compra.", "warning")
    return redirect(url_for("main.purchase_order_detail", order_id=order.id))


@main_bp.post("/compras/<int:order_id>/cancelar")
@permission_required("manage_purchases")
def cancel_purchase_order(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Apenas pedidos em rascunho podem ser cancelados.", "danger")
        return redirect(url_for("main.purchase_order_detail", order_id=order.id))

    db.session.delete(order)
    db.session.commit()
    _audit("purchase:cancel", entity_type="purchase_order", entity_id=order_id)
    flash("Pedido de compra cancelado.", "warning")
    return redirect(url_for("main.purchase_orders"))


@main_bp.post("/compras/<int:order_id>/receber")
@permission_required("manage_purchases")
def receive_purchase(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    try:
        receive_purchase_order(order)
        _audit("purchase:receive", entity_type="purchase_order", entity_id=order.id)
        flash(f"Pedido de compra #{order.id} recebido com sucesso.", "success")
    except StockError as exc:
        db.session.rollback()
        flash(f"Erro ao receber pedido: {exc}", "danger")
    return redirect(url_for("main.purchase_order_detail", order_id=order.id))


@main_bp.route("/vendas", methods=["GET", "POST"])
@permission_required("manage_sales")
def sales_orders():
    if request.method == "POST":
        customer_id = request.form.get("customer_id", "")
        quick_customer_name = request.form.get("quick_customer_name", "").strip()

        if not customer_id.isdigit() and quick_customer_name:
            customer = Customer(
                name=quick_customer_name,
                email=request.form.get("quick_customer_email", "").strip() or None,
                phone=request.form.get("quick_customer_phone", "").strip() or None,
            )
            db.session.add(customer)
            db.session.flush()
            customer_id = str(customer.id)

        order = SalesOrder(
            customer_id=int(customer_id) if customer_id.isdigit() else None,
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(order)
        db.session.commit()
        _audit("sales:create", entity_type="sales_order", entity_id=order.id)
        flash(f"Pedido de venda #{order.id} criado.", "success")
        return redirect(url_for("main.sales_order_detail", order_id=order.id))

    status = request.args.get("status", "").strip()
    customer_filter = request.args.get("customer_id", "").strip()
    start_date = _parse_date_or_none(request.args.get("start_date", ""))
    end_date = _parse_date_or_none(request.args.get("end_date", ""))

    orders_query = SalesOrder.query
    if status:
        orders_query = orders_query.filter(SalesOrder.status == status)
    if customer_filter.isdigit():
        orders_query = orders_query.filter(SalesOrder.customer_id == int(customer_filter))
    if start_date:
        orders_query = orders_query.filter(SalesOrder.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        orders_query = orders_query.filter(SalesOrder.created_at <= datetime.combine(end_date, datetime.max.time()))

    page = _get_page_arg()
    per_page = 20
    orders, total, has_prev, has_next = _paginate(
        orders_query.order_by(SalesOrder.created_at.desc()), page, per_page
    )
    customers_list = Customer.query.order_by(Customer.name.asc()).all()
    return render_template(
        "sales_orders.html",
        orders=orders,
        customers=customers_list,
        selected_status=status,
        selected_customer=customer_filter,
        selected_start_date=request.args.get("start_date", ""),
        selected_end_date=request.args.get("end_date", ""),
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
    )


@main_bp.route("/vendas/<int:order_id>", methods=["GET", "POST"])
@permission_required("manage_sales")
def sales_order_detail(order_id):
    order = SalesOrder.query.get_or_404(order_id)

    if request.method == "POST":
        if order.status != "rascunho":
            flash("Nao e possivel editar venda ja concluida.", "danger")
            return redirect(url_for("main.sales_order_detail", order_id=order.id))

        product_id = request.form.get("product_id", "")
        quantity = request.form.get("quantity", "")
        if not product_id.isdigit() or not quantity.isdigit() or int(quantity) <= 0:
            flash("Produto e quantidade validos sao obrigatorios.", "danger")
            return redirect(url_for("main.sales_order_detail", order_id=order.id))

        item = SalesOrderItem(
            sales_order_id=order.id,
            product_id=int(product_id),
            quantity=int(quantity),
            unit_price=request.form.get("unit_price", 0) or 0,
        )
        db.session.add(item)
        db.session.commit()
        _audit("sales_item:create", entity_type="sales_order", entity_id=order.id)
        flash("Item adicionado ao pedido de venda.", "success")
        return redirect(url_for("main.sales_order_detail", order_id=order.id))

    products = Product.query.order_by(Product.name.asc()).all()
    customers_list = Customer.query.order_by(Customer.name.asc()).all()
    return render_template(
        "sales_order_detail.html", order=order, products=products, customers=customers_list
    )


@main_bp.post("/vendas/<int:order_id>/editar")
@permission_required("manage_sales")
def update_sales_order(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Nao e possivel editar venda concluida.", "danger")
        return redirect(url_for("main.sales_order_detail", order_id=order.id))

    before = {
        "customer_id": order.customer_id,
        "notes": order.notes,
    }

    customer_id = request.form.get("customer_id", "")
    order.customer_id = int(customer_id) if customer_id.isdigit() else None
    order.notes = request.form.get("notes", "").strip() or None

    after = {
        "customer_id": order.customer_id,
        "notes": order.notes,
    }

    db.session.commit()
    _audit_changes("sales:update", "sales_order", order.id, before, after)
    flash("Pedido de venda atualizado.", "success")
    return redirect(url_for("main.sales_order_detail", order_id=order.id))


@main_bp.post("/vendas/<int:order_id>/itens/<int:item_id>/editar")
@permission_required("manage_sales")
def update_sales_item(order_id, item_id):
    order = SalesOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Nao e possivel editar itens de venda concluida.", "danger")
        return redirect(url_for("main.sales_order_detail", order_id=order.id))

    item = SalesOrderItem.query.filter_by(id=item_id, sales_order_id=order.id).first_or_404()
    quantity = request.form.get("quantity", "")
    if not quantity.isdigit() or int(quantity) <= 0:
        flash("Quantidade invalida.", "danger")
        return redirect(url_for("main.sales_order_detail", order_id=order.id))

    before = {
        "quantity": item.quantity,
        "unit_price": float(item.unit_price or 0),
    }

    item.quantity = int(quantity)
    item.unit_price = request.form.get("unit_price", 0) or 0

    after = {
        "quantity": item.quantity,
        "unit_price": float(item.unit_price or 0),
    }

    db.session.commit()
    _audit_changes("sales_item:update", "sales_order_item", item.id, before, after)
    flash("Item de venda atualizado.", "success")
    return redirect(url_for("main.sales_order_detail", order_id=order.id))


@main_bp.post("/vendas/<int:order_id>/itens/<int:item_id>/deletar")
@permission_required("manage_sales")
def delete_sales_item(order_id, item_id):
    order = SalesOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Nao e possivel remover itens de venda concluida.", "danger")
        return redirect(url_for("main.sales_order_detail", order_id=order.id))

    item = SalesOrderItem.query.filter_by(id=item_id, sales_order_id=order.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    _audit("sales_item:delete", entity_type="sales_order_item", entity_id=item_id)
    flash("Item removido do pedido de venda.", "warning")
    return redirect(url_for("main.sales_order_detail", order_id=order.id))


@main_bp.post("/vendas/<int:order_id>/cancelar")
@permission_required("manage_sales")
def cancel_sales_order(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    if order.status != "rascunho":
        flash("Apenas vendas em rascunho podem ser canceladas.", "danger")
        return redirect(url_for("main.sales_order_detail", order_id=order.id))

    db.session.delete(order)
    db.session.commit()
    _audit("sales:cancel", entity_type="sales_order", entity_id=order_id)
    flash("Pedido de venda cancelado.", "warning")
    return redirect(url_for("main.sales_orders"))


@main_bp.post("/vendas/<int:order_id>/concluir")
@permission_required("manage_sales")
def complete_sale(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    try:
        complete_sales_order(order)
        _audit("sales:complete", entity_type="sales_order", entity_id=order.id)
        flash(f"Pedido de venda #{order.id} concluido com sucesso.", "success")
    except StockError as exc:
        db.session.rollback()
        flash(f"Erro ao concluir venda: {exc}", "danger")
    return redirect(url_for("main.sales_order_detail", order_id=order.id))


@main_bp.route("/lotes")
@permission_required("manage_batches")
def batches():
    status = request.args.get("status", "todos")
    product_filter = request.args.get("product_id", "").strip()
    today = date.today()
    soon_limit = date.fromordinal(today.toordinal() + 30)

    query = ProductBatch.query.filter(ProductBatch.quantity_available > 0)
    if product_filter.isdigit():
        query = query.filter(ProductBatch.product_id == int(product_filter))
    if status == "vencido":
        query = query.filter(ProductBatch.expiry_date.isnot(None)).filter(ProductBatch.expiry_date < today)
    elif status == "proximo":
        query = (
            query.filter(ProductBatch.expiry_date.isnot(None))
            .filter(ProductBatch.expiry_date >= today)
            .filter(ProductBatch.expiry_date <= soon_limit)
        )

    page = _get_page_arg()
    per_page = 25
    batches_list, total, has_prev, has_next = _paginate(
        query.order_by(ProductBatch.expiry_date.asc(), ProductBatch.created_at.desc()), page, per_page
    )
    products = Product.query.order_by(Product.name.asc()).all()
    return render_template(
        "batches.html",
        batches=batches_list,
        selected_status=status,
        selected_product=product_filter,
        products=products,
        today=today,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
    )


@main_bp.post("/lotes/<int:batch_id>/baixa")
@permission_required("manage_batches")
def writeoff_batch(batch_id):
    batch = ProductBatch.query.get_or_404(batch_id)
    quantity = request.form.get("quantity", "")
    if not quantity.isdigit() or int(quantity) <= 0:
        flash("Quantidade de baixa invalida.", "danger")
        return redirect(url_for("main.batches"))

    qty = int(quantity)
    if qty > batch.quantity_available:
        flash("Quantidade maior que saldo disponivel do lote.", "danger")
        return redirect(url_for("main.batches"))

    batch.quantity_available -= qty
    batch.product.quantity -= qty
    movement = StockMovement(
        product_id=batch.product_id,
        movement_type="saida",
        quantity=qty,
        reason=request.form.get("reason", "Baixa manual de lote") or "Baixa manual de lote",
        reference=f"LOTE-{batch.id}",
    )
    db.session.add(movement)
    db.session.commit()
    _audit("batch:writeoff", entity_type="product_batch", entity_id=batch.id)
    flash("Baixa de lote registrada com sucesso.", "success")
    return redirect(url_for("main.batches"))


@main_bp.route("/produtos", methods=["GET", "POST"])
@permission_required("manage_products")
def products():
    if request.method == "POST":
        try:
            sku = request.form.get("sku", "").strip()
            name = request.form.get("name", "").strip()
            create_product(request.form)
            created = Product.query.filter_by(sku=sku).order_by(Product.created_at.desc()).first()
            _audit(
                "product:create",
                detail=f"{sku} - {name}" if sku or name else None,
                entity_type="product",
                entity_id=created.id if created else None,
            )
            flash("Produto criado com sucesso.", "success")
        except Exception as exc:
            db.session.rollback()
            flash(f"Erro ao criar produto: {exc}", "danger")
        return redirect(url_for("main.products"))

    query = request.args.get("q", "").strip()
    products_query = Product.query
    if query:
        products_query = products_query.filter(
            Product.name.ilike(f"%{query}%") | Product.sku.ilike(f"%{query}%")
        )

    page = _get_page_arg()
    per_page = 25
    products_list, total, has_prev, has_next = _paginate(
        products_query.order_by(Product.name.asc()), page, per_page
    )
    categories = Category.query.order_by(Category.name.asc()).all()
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()

    return render_template(
        "products.html",
        products=products_list,
        categories=categories,
        suppliers=suppliers,
        query=query,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
    )


@main_bp.post("/produtos/rapido")
@permission_required("manage_products")
def create_product_quick():
    next_url = request.form.get("next_url") or url_for("main.products")
    payload = {
        "sku": request.form.get("sku", ""),
        "name": request.form.get("name", ""),
        "description": request.form.get("description", ""),
        "cost_price": request.form.get("cost_price", "0"),
        "sale_price": request.form.get("sale_price", "0"),
        "quantity": request.form.get("quantity", "0"),
        "min_stock": request.form.get("min_stock", "0"),
        "supplier_id": request.form.get("supplier_id", ""),
        "category_id": request.form.get("category_id", ""),
    }

    try:
        create_product(payload)
        flash("Produto criado rapidamente com sucesso.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Erro ao criar produto rapido: {exc}", "danger")

    return redirect(next_url)


@main_bp.post("/produtos/<int:product_id>/editar")
@permission_required("manage_products")
def update_product_route(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        before = {
            "sku": product.sku,
            "name": product.name,
            "cost_price": float(product.cost_price or 0),
            "sale_price": float(product.sale_price or 0),
            "min_stock": product.min_stock,
            "category_id": product.category_id,
            "supplier_id": product.supplier_id,
        }
        update_product(product, request.form)
        after = {
            "sku": product.sku,
            "name": product.name,
            "cost_price": float(product.cost_price or 0),
            "sale_price": float(product.sale_price or 0),
            "min_stock": product.min_stock,
            "category_id": product.category_id,
            "supplier_id": product.supplier_id,
        }
        _audit_changes("product:update", "product", product.id, before, after)
        flash("Produto atualizado com sucesso.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Erro ao atualizar produto: {exc}", "danger")
    return redirect(url_for("main.products"))


@main_bp.post("/produtos/<int:product_id>/deletar")
@permission_required("manage_products")
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    product_name = product.name
    db.session.delete(product)
    db.session.commit()
    _audit("product:delete", detail=product_name, entity_type="product", entity_id=product_id)
    flash("Produto removido.", "warning")
    return redirect(url_for("main.products"))


@main_bp.route("/categorias", methods=["GET", "POST"])
@permission_required("manage_categories")
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Nome da categoria e obrigatorio.", "danger")
            return redirect(url_for("main.categories"))

        category = Category(name=name, description=description)
        db.session.add(category)
        try:
            db.session.commit()
            _audit("category:create", detail=category.name, entity_type="category", entity_id=category.id)
            flash("Categoria criada.", "success")
        except Exception:
            db.session.rollback()
            flash("Nao foi possivel criar categoria (nome pode estar duplicado).", "danger")

        return redirect(url_for("main.categories"))

    categories_list = Category.query.order_by(Category.name.asc()).all()
    return render_template("categories.html", categories=categories_list)


@main_bp.route("/fornecedores", methods=["GET", "POST"])
@permission_required("manage_suppliers")
def suppliers():
    if request.method == "POST":
        supplier = Supplier(
            name=request.form.get("name", "").strip(),
            contact_name=request.form.get("contact_name", "").strip() or None,
            email=request.form.get("email", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
        )

        if not supplier.name:
            flash("Nome do fornecedor e obrigatorio.", "danger")
            return redirect(url_for("main.suppliers"))

        db.session.add(supplier)
        db.session.commit()
        _audit("supplier:create", detail=supplier.name, entity_type="supplier", entity_id=supplier.id)
        flash("Fornecedor cadastrado.", "success")
        return redirect(url_for("main.suppliers"))

    suppliers_list = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template("suppliers.html", suppliers=suppliers_list)


@main_bp.post("/fornecedores/<int:supplier_id>/deletar")
@permission_required("manage_suppliers")
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    if supplier.products:
        flash("Fornecedor possui produtos vinculados e nao pode ser removido.", "danger")
        return redirect(url_for("main.suppliers"))

    supplier_name = supplier.name
    db.session.delete(supplier)
    db.session.commit()
    _audit("supplier:delete", detail=supplier_name, entity_type="supplier", entity_id=supplier_id)
    flash("Fornecedor removido.", "warning")
    return redirect(url_for("main.suppliers"))


@main_bp.route("/movimentacoes", methods=["GET", "POST"])
@permission_required("manage_movements")
def movements():
    if request.method == "POST":
        try:
            product_id = int(request.form.get("product_id"))
            movement_type = request.form.get("movement_type")
            quantity = int(request.form.get("quantity", 0))
            reason = request.form.get("reason", "")
            reference = request.form.get("reference", "")
            create_movement(
                product_id=product_id,
                movement_type=movement_type,
                quantity=quantity,
                reason=reason,
                reference=reference,
            )
            product = Product.query.get(product_id)
            _audit(
                "movement:create",
                detail=f"{movement_type} {quantity}",
                entity_type="product",
                entity_id=product.id if product else None,
            )
            flash("Movimentacao registrada.", "success")
        except (ValueError, StockError) as exc:
            db.session.rollback()
            flash(f"Erro na movimentacao: {exc}", "danger")
        return redirect(url_for("main.movements"))

    movement_type = request.args.get("type", "").strip()
    product_id = request.args.get("product_id", "").strip()

    movements_query = StockMovement.query
    if movement_type:
        movements_query = movements_query.filter_by(movement_type=movement_type)
    if product_id.isdigit():
        movements_query = movements_query.filter_by(product_id=int(product_id))

    page = _get_page_arg()
    per_page = 25
    movements_list, total, has_prev, has_next = _paginate(
        movements_query.order_by(StockMovement.created_at.desc()), page, per_page
    )
    products = Product.query.order_by(Product.name.asc()).all()

    return render_template(
        "movements.html",
        movements=movements_list,
        products=products,
        selected_type=movement_type,
        selected_product=product_id,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
    )


@main_bp.route("/relatorios")
@permission_required("view_reports")
def reports():
    products = Product.query.order_by(Product.name.asc()).all()
    movements_list = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(50).all()
    total_value = sum(p.stock_value for p in products)
    purchases_received = PurchaseOrder.query.filter_by(status="recebido").count()
    sales_completed = SalesOrder.query.filter_by(status="concluido").count()
    sales_revenue = sum(
        (item.unit_price or 0) * item.quantity
        for order in SalesOrder.query.filter_by(status="concluido").all()
        for item in order.items
    )
    near_expiry = expiring_batches(30)

    return render_template(
        "reports.html",
        products=products,
        movements=movements_list,
        total_value=total_value,
        purchases_received=purchases_received,
        sales_completed=sales_completed,
        sales_revenue=sales_revenue,
        near_expiry=near_expiry,
    )


@main_bp.route("/financeiro", methods=["GET", "POST"])
@permission_required("view_financial")
def financial_entries():
    if request.method == "POST":
        if "manage_financial" not in g.get("permission_keys", set()):
            flash("Voce nao tem permissao para alterar lancamentos financeiros.", "danger")
            return redirect(url_for("main.financial_entries"))

        entry_type = request.form.get("entry_type", "").strip()
        status = request.form.get("status", "pendente").strip() or "pendente"
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip() or None
        amount_raw = request.form.get("amount", "0").strip()
        due_date = _parse_date_or_none(request.form.get("due_date", ""))
        reference = request.form.get("reference", "").strip() or None

        if entry_type not in {"receber", "pagar"}:
            flash("Tipo de lancamento invalido.", "danger")
            return redirect(url_for("main.financial_entries"))
        if status not in {"pendente", "pago", "cancelado"}:
            flash("Status de lancamento invalido.", "danger")
            return redirect(url_for("main.financial_entries"))
        if not description:
            flash("Descricao e obrigatoria.", "danger")
            return redirect(url_for("main.financial_entries"))

        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            flash("Valor invalido. Informe valor numerico maior que zero.", "danger")
            return redirect(url_for("main.financial_entries"))

        entry = FinancialEntry(
            entry_type=entry_type,
            status=status,
            description=description,
            category=category,
            amount=amount,
            due_date=due_date,
            paid_at=datetime.now(timezone.utc) if status == "pago" else None,
            reference=reference,
        )
        db.session.add(entry)
        db.session.commit()
        _audit("financial:create", detail=description, entity_type="financial_entry", entity_id=entry.id)
        flash("Lancamento financeiro criado.", "success")
        return redirect(url_for("main.financial_entries"))

    entry_type = request.args.get("entry_type", "").strip()
    status = request.args.get("status", "").strip()
    start_date = _parse_date_or_none(request.args.get("start_date", ""))
    end_date = _parse_date_or_none(request.args.get("end_date", ""))

    query = FinancialEntry.query
    if entry_type in {"receber", "pagar"}:
        query = query.filter(FinancialEntry.entry_type == entry_type)
    if status in {"pendente", "pago", "cancelado"}:
        query = query.filter(FinancialEntry.status == status)
    if start_date:
        query = query.filter(FinancialEntry.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(FinancialEntry.created_at <= datetime.combine(end_date, datetime.max.time()))

    page = _get_page_arg()
    per_page = 20
    entries, total, has_prev, has_next = _paginate(query.order_by(FinancialEntry.created_at.desc()), page, per_page)
    summary = financial_summary(start_date=start_date, end_date=end_date)
    cashflow = cashflow_last_days(14)

    return render_template(
        "financial.html",
        entries=entries,
        total=total,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        selected_type=entry_type,
        selected_status=status,
        selected_start_date=request.args.get("start_date", ""),
        selected_end_date=request.args.get("end_date", ""),
        summary=summary,
        cashflow=cashflow,
    )


@main_bp.post("/financeiro/<int:entry_id>/marcar-pago")
@permission_required("manage_financial")
def mark_financial_paid(entry_id):
    entry = FinancialEntry.query.get_or_404(entry_id)
    if entry.status == "cancelado":
        flash("Lancamento cancelado nao pode ser marcado como pago.", "danger")
        return redirect(url_for("main.financial_entries"))

    entry.status = "pago"
    entry.paid_at = datetime.now(timezone.utc)
    db.session.commit()
    _audit("financial:mark_paid", detail=entry.description, entity_type="financial_entry", entity_id=entry.id)
    flash("Lancamento marcado como pago.", "success")
    return redirect(url_for("main.financial_entries"))


@main_bp.post("/financeiro/<int:entry_id>/cancelar")
@permission_required("manage_financial")
def cancel_financial_entry(entry_id):
    entry = FinancialEntry.query.get_or_404(entry_id)
    entry.status = "cancelado"
    db.session.commit()
    _audit("financial:cancel", detail=entry.description, entity_type="financial_entry", entity_id=entry.id)
    flash("Lancamento cancelado.", "warning")
    return redirect(url_for("main.financial_entries"))


@main_bp.route("/reposicao")
@permission_required("view_replenishment")
def replenishment():
    class_filter = request.args.get("class", "").strip().upper()
    only_needed = request.args.get("only_needed", "1") == "1"

    suggestions = abc_and_replenishment()
    if class_filter in {"A", "B", "C"}:
        suggestions = [row for row in suggestions if row["abc_class"] == class_filter]
    if only_needed:
        suggestions = [row for row in suggestions if row["needs_restock"]]

    return render_template(
        "replenishment.html",
        suggestions=suggestions,
        selected_class=class_filter,
        only_needed=only_needed,
    )


@main_bp.route("/executivo")
@permission_required("view_reports")
def executive_dashboard():
    summary = financial_summary()
    suggestions = abc_and_replenishment()
    need_restock = [row for row in suggestions if row["needs_restock"]]
    low_stock_products = (
        Product.query.filter(Product.quantity <= Product.min_stock)
        .order_by(Product.quantity.asc())
        .limit(10)
        .all()
    )

    return render_template(
        "executive.html",
        summary=summary,
        restock_count=len(need_restock),
        top_restock=need_restock[:10],
        low_stock_products=low_stock_products,
    )


@main_bp.get("/relatorios/exportar/produtos.csv")
@permission_required("view_reports")
def export_products_csv():
    products = Product.query.order_by(Product.name.asc()).all()
    rows = [
        [
            p.sku,
            p.name,
            p.category.name if p.category else "",
            p.supplier.name if p.supplier else "",
            p.quantity,
            p.min_stock,
            p.cost_price,
            p.sale_price,
        ]
        for p in products
    ]
    return csv_response(
        "produtos.csv",
        [
            "SKU",
            "Nome",
            "Categoria",
            "Fornecedor",
            "Quantidade",
            "Estoque Minimo",
            "Preco Custo",
            "Preco Venda",
        ],
        rows,
    )


@main_bp.get("/relatorios/exportar/movimentacoes.csv")
@permission_required("view_reports")
def export_movements_csv():
    movements_list = StockMovement.query.order_by(StockMovement.created_at.desc()).all()
    rows = [
        [
            m.created_at.strftime("%Y-%m-%d %H:%M"),
            m.product.sku,
            m.product.name,
            m.movement_type,
            m.quantity,
            m.reason or "",
            m.reference or "",
        ]
        for m in movements_list
    ]
    return csv_response(
        "movimentacoes.csv",
        ["Data", "SKU", "Produto", "Tipo", "Quantidade", "Motivo", "Referencia"],
        rows,
    )


@main_bp.route("/usuarios", methods=["GET", "POST"])
@permission_required("manage_users")
def users_management():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "operador")

        if role not in {"admin", "operador"}:
            flash("Perfil invalido.", "danger")
            return redirect(url_for("main.users_management"))

        if not username or len(password) < 6:
            flash("Informe usuario e senha com pelo menos 6 caracteres.", "danger")
            return redirect(url_for("main.users_management"))

        if User.query.filter_by(username=username).first():
            flash("Nome de usuario ja cadastrado.", "danger")
            return redirect(url_for("main.users_management"))

        user = User(username=username, role=role, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        assign_default_permissions_for_user(user.id, user.role)
        _audit("user:create", detail=user.username, entity_type="user", entity_id=user.id)
        flash("Usuario criado com sucesso.", "success")
        return redirect(url_for("main.users_management"))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users.html", users=users)


@main_bp.post("/usuarios/<int:user_id>/alternar-status")
@permission_required("manage_users")
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == g.user.id:
        flash("Voce nao pode desativar seu proprio usuario.", "danger")
        return redirect(url_for("main.users_management"))

    user.is_active = not user.is_active
    db.session.commit()
    _audit("user:toggle_status", detail=f"{user.username}:{user.is_active}", entity_type="user", entity_id=user.id)
    flash("Status do usuario atualizado.", "success")
    return redirect(url_for("main.users_management"))


@main_bp.post("/usuarios/<int:user_id>/resetar-senha")
@permission_required("manage_users")
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "")
    if len(new_password) < 6:
        flash("A nova senha precisa ter pelo menos 6 caracteres.", "danger")
        return redirect(url_for("main.users_management"))

    user.set_password(new_password)
    db.session.commit()
    _audit("user:reset_password", detail=user.username, entity_type="user", entity_id=user.id)
    flash("Senha redefinida com sucesso.", "success")
    return redirect(url_for("main.users_management"))


@main_bp.route("/sistema", methods=["GET", "POST"])
@permission_required("manage_system")
def system_settings():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "create_backup":
                backup_file = create_backup(tag="manual")
                _audit("system:backup_create", detail=backup_file.name, entity_type="system")
                flash(f"Backup criado: {backup_file.name}", "success")
            elif action == "restore_backup":
                filename = request.form.get("backup_file", "")
                restore_backup(filename)
                _audit("system:backup_restore", detail=filename, entity_type="system")
                flash("Backup restaurado com sucesso.", "success")
            else:
                flash("Acao invalida.", "danger")
        except Exception as exc:
            flash(f"Erro ao processar backup: {exc}", "danger")

        return redirect(url_for("main.system_settings"))

    backups = [
        {
            "name": b.name,
            "size_kb": round(b.stat().st_size / 1024, 1),
            "modified_at": datetime.fromtimestamp(b.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
        }
        for b in list_backups()
    ]
    return render_template("system.html", backups=backups)


@main_bp.route("/usuarios/<int:user_id>/permissoes", methods=["GET", "POST"])
@permission_required("manage_permissions")
def user_permissions(user_id):
    user = User.query.get_or_404(user_id)
    permissions = Permission.query.order_by(Permission.label.asc()).all()

    if request.method == "POST":
        selected = request.form.getlist("permissions")
        if user.id == g.user.id and "manage_permissions" not in selected:
            selected.append("manage_permissions")
            flash(
                "A permissao 'Gerenciar permissoes' do seu proprio usuario foi mantida para evitar bloqueio.",
                "warning",
            )
        set_user_permissions(user.id, selected)
        _audit(
            "permissions:update",
            detail=f"usuario={user.username} qtd={len(selected)}",
            entity_type="user",
            entity_id=user.id,
        )
        flash("Permissoes atualizadas.", "success")
        return redirect(url_for("main.users_management"))

    selected_keys = {
        row.permission.key
        for row in UserPermission.query.join(Permission, Permission.id == UserPermission.permission_id)
        .filter(UserPermission.user_id == user.id)
        .all()
    }
    return render_template(
        "user_permissions.html",
        target_user=user,
        permissions=permissions,
        selected_keys=selected_keys,
    )


@main_bp.route("/usuarios/permissoes/matriz", methods=["GET", "POST"])
@permission_required("manage_permissions")
def permissions_matrix():
    users = User.query.order_by(User.username.asc()).all()
    permissions = Permission.query.order_by(Permission.label.asc()).all()

    if request.method == "POST":
        submitted_user_ids = []
        for raw_user_id in request.form.getlist("user_ids"):
            if raw_user_id.isdigit():
                submitted_user_ids.append(int(raw_user_id))

        updated_count = 0
        for user_id in dict.fromkeys(submitted_user_ids):
            selected = [key for key in request.form.getlist(f"perm_{user_id}") if key]
            if user_id == g.user.id and "manage_permissions" not in selected:
                selected.append("manage_permissions")
            set_user_permissions(user_id, selected)
            updated_count += 1

        if g.user.id in submitted_user_ids:
            flash(
                "A permissao 'Gerenciar permissoes' do seu proprio usuario foi mantida para evitar bloqueio.",
                "warning",
            )

        _audit("permissions:matrix_update", detail=f"usuarios={updated_count}")
        flash("Matriz de permissoes atualizada.", "success")
        return redirect(url_for("main.permissions_matrix"))

    user_permission_rows = UserPermission.query.join(Permission, Permission.id == UserPermission.permission_id).all()
    matrix = {u.id: set() for u in users}
    for row in user_permission_rows:
        matrix[row.user_id].add(row.permission.key)

    return render_template(
        "permissions_matrix.html",
        users=users,
        permissions=permissions,
        matrix=matrix,
    )


@main_bp.route("/auditoria")
@permission_required("view_audit")
def audit_logs():
    username = request.args.get("username", "").strip()
    action = request.args.get("action", "").strip()
    entity_type = request.args.get("entity_type", "").strip()
    entity_id = request.args.get("entity_id", "").strip()

    page = max(int(request.args.get("page", 1) or 1), 1)
    per_page = 50

    query = AuditLog.query
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.filter(AuditLog.entity_type.ilike(f"%{entity_type}%"))
    if entity_id.isdigit():
        query = query.filter(AuditLog.entity_id == int(entity_id))

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    has_prev = page > 1
    has_next = page * per_page < total

    return render_template(
        "audit_logs.html",
        logs=logs,
        username=username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
    )


@main_bp.route("/importacoes/produtos", methods=["GET", "POST"])
@permission_required("import_products")
def import_products():
    if request.method == "POST":
        csv_file = request.files.get("file")
        dry_run = request.form.get("dry_run") == "1"
        if not csv_file or not csv_file.filename.lower().endswith(".csv"):
            flash("Envie um arquivo CSV valido.", "danger")
            return redirect(url_for("main.import_products"))

        content = csv_file.read().decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(StringIO(content))

        required_headers = {"sku", "name"}
        found_headers = {h.strip().lower() for h in (reader.fieldnames or []) if h}
        if not found_headers:
            flash("CSV vazio ou sem cabecalho.", "danger")
            return redirect(url_for("main.import_products"))
        if not required_headers.issubset(found_headers):
            missing = ", ".join(sorted(required_headers - found_headers))
            flash(f"Cabecalho CSV invalido. Colunas obrigatorias: {missing}", "danger")
            return redirect(url_for("main.import_products"))

        created = 0
        updated = 0
        errors = []

        for line_number, row in enumerate(reader, start=2):
            sku = (row.get("sku") or "").strip()
            name = (row.get("name") or "").strip()
            if not sku or not name:
                errors.append(
                    {
                        "line": line_number,
                        "sku": sku,
                        "name": name,
                        "error": "SKU e nome sao obrigatorios.",
                    }
                )
                continue

            try:
                quantity = int((row.get("quantity") or 0) or 0)
                min_stock = int((row.get("min_stock") or 0) or 0)
                cost_price = float((row.get("cost_price") or 0) or 0)
                sale_price = float((row.get("sale_price") or 0) or 0)

                if quantity < 0 or min_stock < 0 or cost_price < 0 or sale_price < 0:
                    raise ValueError("Valores numericos devem ser maiores ou iguais a zero")

                product = Product.query.filter_by(sku=sku).first()
                if product:
                    product.name = name
                    product.description = (row.get("description") or "").strip() or None
                    product.cost_price = cost_price
                    product.sale_price = sale_price
                    product.min_stock = min_stock
                    updated += 1
                else:
                    product = Product(
                        sku=sku,
                        name=name,
                        description=(row.get("description") or "").strip() or None,
                        cost_price=cost_price,
                        sale_price=sale_price,
                        quantity=quantity,
                        min_stock=min_stock,
                    )
                    db.session.add(product)
                    created += 1
            except Exception as exc:
                errors.append(
                    {
                        "line": line_number,
                        "sku": sku,
                        "name": name,
                        "error": str(exc),
                    }
                )

        if dry_run:
            db.session.rollback()
        else:
            db.session.commit()

        session["import_product_errors"] = errors
        session["import_product_summary"] = {
            "created": created,
            "updated": updated,
            "errors": len(errors),
            "dry_run": dry_run,
        }

        audit_log(
            username=g.user.username,
            action="products:import_csv_dry_run" if dry_run else "products:import_csv",
            endpoint=request.endpoint,
            path=request.path,
            method=request.method,
            status_code=200,
            detail=f"created={created} updated={updated} errors={len(errors)}",
            entity_type="product",
        )
        if dry_run:
            flash(
                f"Simulacao concluida. Seriam criados: {created}, atualizados: {updated}, erros: {len(errors)}",
                "warning",
            )
        else:
            flash(
                f"Importacao concluida. Criados: {created}, Atualizados: {updated}, Erros: {len(errors)}",
                "success",
            )
        return redirect(url_for("main.import_products"))

    summary = session.get("import_product_summary")
    errors = session.get("import_product_errors", [])
    return render_template("import_products.html", summary=summary, errors=errors)


@main_bp.get("/importacoes/produtos/erros.csv")
@permission_required("import_products")
def export_product_import_errors_csv():
    errors = session.get("import_product_errors", [])
    rows = [[e.get("line"), e.get("sku"), e.get("name"), e.get("error")] for e in errors]
    return csv_response("import_errors_produtos.csv", ["Linha", "SKU", "Nome", "Erro"], rows)
