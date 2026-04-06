from decimal import Decimal, InvalidOperation

from .models import Product, StockMovement, db


class StockError(ValueError):
    pass


def parse_decimal(value, default="0"):
    try:
        return Decimal(str(value or default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def apply_stock_movement(product: Product, movement_type: str, quantity: int):
    if quantity <= 0:
        raise StockError("A quantidade deve ser maior que zero.")

    if movement_type == "entrada":
        product.quantity += quantity
    elif movement_type == "saida":
        if product.quantity - quantity < 0:
            raise StockError("Estoque insuficiente para a saida informada.")
        product.quantity -= quantity
    elif movement_type == "ajuste":
        product.quantity = quantity
    else:
        raise StockError("Tipo de movimentacao invalido.")


def create_movement(product_id: int, movement_type: str, quantity: int, reason: str, reference: str):
    product = Product.query.get_or_404(product_id)

    apply_stock_movement(product, movement_type, quantity)

    movement = StockMovement(
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        reason=reason.strip() if reason else None,
        reference=reference.strip() if reference else None,
    )

    db.session.add(movement)
    db.session.commit()


def create_product(payload):
    product = Product(
        sku=payload.get("sku", "").strip(),
        name=payload.get("name", "").strip(),
        description=payload.get("description", "").strip() or None,
        cost_price=parse_decimal(payload.get("cost_price")),
        sale_price=parse_decimal(payload.get("sale_price")),
        quantity=int(payload.get("quantity", 0) or 0),
        min_stock=int(payload.get("min_stock", 0) or 0),
        category_id=int(payload["category_id"]) if payload.get("category_id") else None,
        supplier_id=int(payload["supplier_id"]) if payload.get("supplier_id") else None,
    )

    if not product.sku or not product.name:
        raise StockError("SKU e nome do produto sao obrigatorios.")

    db.session.add(product)
    db.session.commit()


def update_product(product: Product, payload):
    product.sku = payload.get("sku", product.sku).strip()
    product.name = payload.get("name", product.name).strip()
    product.description = payload.get("description", "").strip() or None
    product.cost_price = parse_decimal(payload.get("cost_price", product.cost_price))
    product.sale_price = parse_decimal(payload.get("sale_price", product.sale_price))
    product.min_stock = int(payload.get("min_stock", product.min_stock) or 0)
    product.category_id = int(payload["category_id"]) if payload.get("category_id") else None
    product.supplier_id = int(payload["supplier_id"]) if payload.get("supplier_id") else None

    if not product.sku or not product.name:
        raise StockError("SKU e nome do produto sao obrigatorios.")

    db.session.commit()
