from datetime import datetime, timezone
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="operador", nullable=False)  # admin, operador
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    products = db.relationship("Product", back_populates="category", lazy=True)


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    products = db.relationship("Product", back_populates="supplier", lazy=True)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    document = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sales_orders = db.relationship("SalesOrder", back_populates="customer", lazy=True)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    cost_price = db.Column(db.Numeric(10, 2), default=0)
    sale_price = db.Column(db.Numeric(10, 2), default=0)
    quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)

    category = db.relationship("Category", back_populates="products")
    supplier = db.relationship("Supplier", back_populates="products")
    movements = db.relationship(
        "StockMovement", back_populates="product", cascade="all, delete-orphan", lazy=True
    )
    batches = db.relationship(
        "ProductBatch", back_populates="product", cascade="all, delete-orphan", lazy=True
    )
    purchase_items = db.relationship("PurchaseOrderItem", back_populates="product", lazy=True)
    sales_items = db.relationship("SalesOrderItem", back_populates="product", lazy=True)

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock

    @property
    def stock_value(self):
        return Decimal(self.quantity) * Decimal(self.cost_price or 0)


class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    movement_type = db.Column(db.String(20), nullable=False)  # entrada, saida, ajuste
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    reference = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product = db.relationship("Product", back_populates="movements")


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="rascunho", nullable=False)  # rascunho, recebido
    notes = db.Column(db.String(255), nullable=True)
    expected_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    received_at = db.Column(db.DateTime, nullable=True)

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier")

    items = db.relationship(
        "PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan", lazy=True
    )

    @property
    def total_cost(self):
        return sum((item.unit_cost or 0) * item.quantity for item in self.items)


class PurchaseOrderItem(db.Model):
    __tablename__ = "purchase_order_items"

    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), default=0)
    lot_code = db.Column(db.String(60), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)

    purchase_order_id = db.Column(db.Integer, db.ForeignKey("purchase_orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    purchase_order = db.relationship("PurchaseOrder", back_populates="items")
    product = db.relationship("Product", back_populates="purchase_items")


class SalesOrder(db.Model):
    __tablename__ = "sales_orders"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="rascunho", nullable=False)  # rascunho, concluido
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    customer = db.relationship("Customer", back_populates="sales_orders")

    items = db.relationship(
        "SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan", lazy=True
    )

    @property
    def total_amount(self):
        return sum((item.unit_price or 0) * item.quantity for item in self.items)


class SalesOrderItem(db.Model):
    __tablename__ = "sales_order_items"

    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=0)

    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    sales_order = db.relationship("SalesOrder", back_populates="items")
    product = db.relationship("Product", back_populates="sales_items")


class ProductBatch(db.Model):
    __tablename__ = "product_batches"

    id = db.Column(db.Integer, primary_key=True)
    lot_code = db.Column(db.String(60), nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    quantity_total = db.Column(db.Integer, nullable=False, default=0)
    quantity_available = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    purchase_order_item_id = db.Column(db.Integer, db.ForeignKey("purchase_order_items.id"), nullable=True)

    product = db.relationship("Product", back_populates="batches")

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.now(timezone.utc).date()


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)


class UserPermission(db.Model):
    __tablename__ = "user_permissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False)

    user = db.relationship("User")
    permission = db.relationship("Permission")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    endpoint = db.Column(db.String(120), nullable=True)
    path = db.Column(db.String(255), nullable=True)
    method = db.Column(db.String(10), nullable=True)
    status_code = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.String(255), nullable=True)
    entity_type = db.Column(db.String(80), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class FinancialEntry(db.Model):
    __tablename__ = "financial_entries"

    id = db.Column(db.Integer, primary_key=True)
    entry_type = db.Column(db.String(20), nullable=False)  # receber, pagar
    status = db.Column(db.String(20), default="pendente", nullable=False)  # pendente, pago, cancelado
    description = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    reference = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def is_overdue(self):
        if self.status != "pendente" or not self.due_date:
            return False
        return self.due_date < datetime.now(timezone.utc).date()
