from datetime import datetime, timezone

from .models import (
    Product,
    ProductBatch,
    PurchaseOrder,
    SalesOrder,
    StockMovement,
    db,
)
from .services import StockError


def receive_purchase_order(order: PurchaseOrder):
    if order.status == "recebido":
        raise StockError("Pedido de compra ja foi recebido.")

    if not order.items:
        raise StockError("Pedido de compra sem itens.")

    for item in order.items:
        if item.quantity <= 0:
            raise StockError("Quantidade invalida em item de compra.")

        product = Product.query.get(item.product_id)
        if product is None:
            raise StockError("Produto do item de compra nao encontrado.")

        product.quantity += item.quantity

        batch = ProductBatch(
            product_id=product.id,
            purchase_order_item_id=item.id,
            lot_code=item.lot_code,
            expiry_date=item.expiry_date,
            quantity_total=item.quantity,
            quantity_available=item.quantity,
        )
        db.session.add(batch)

        movement = StockMovement(
            product_id=product.id,
            movement_type="entrada",
            quantity=item.quantity,
            reason=f"Recebimento compra #{order.id}",
            reference=f"COMPRA-{order.id}",
        )
        db.session.add(movement)

    order.status = "recebido"
    order.received_at = datetime.now(timezone.utc)
    db.session.commit()


def _consume_batches(product_id: int, required_qty: int):
    batches = (
        ProductBatch.query.filter_by(product_id=product_id)
        .filter(ProductBatch.quantity_available > 0)
        .order_by(ProductBatch.expiry_date.asc(), ProductBatch.created_at.asc())
        .all()
    )

    remaining = required_qty
    for batch in batches:
        if remaining <= 0:
            break
        used = min(batch.quantity_available, remaining)
        batch.quantity_available -= used
        remaining -= used

    if remaining > 0:
        raise StockError("Nao ha saldo em lotes suficiente para a venda.")


def complete_sales_order(order: SalesOrder):
    if order.status == "concluido":
        raise StockError("Pedido de venda ja foi concluido.")

    if not order.items:
        raise StockError("Pedido de venda sem itens.")

    for item in order.items:
        product = Product.query.get(item.product_id)
        if product is None:
            raise StockError("Produto do item de venda nao encontrado.")
        if item.quantity <= 0:
            raise StockError("Quantidade invalida em item de venda.")
        if product.quantity < item.quantity:
            raise StockError(f"Estoque insuficiente para o produto {product.name}.")

    for item in order.items:
        product = Product.query.get(item.product_id)
        _consume_batches(product.id, item.quantity)
        product.quantity -= item.quantity

        movement = StockMovement(
            product_id=product.id,
            movement_type="saida",
            quantity=item.quantity,
            reason=f"Venda #{order.id}",
            reference=f"VENDA-{order.id}",
        )
        db.session.add(movement)

    order.status = "concluido"
    order.completed_at = datetime.now(timezone.utc)
    db.session.commit()


def expiring_batches(days: int = 30):
    today = datetime.now(timezone.utc).date()
    limit = today.fromordinal(today.toordinal() + days)
    return (
        ProductBatch.query.filter(ProductBatch.expiry_date.isnot(None))
        .filter(ProductBatch.quantity_available > 0)
        .filter(ProductBatch.expiry_date <= limit)
        .order_by(ProductBatch.expiry_date.asc())
        .all()
    )
