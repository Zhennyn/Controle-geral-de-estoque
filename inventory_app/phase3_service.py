from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func

from .models import FinancialEntry, Product, SalesOrder, SalesOrderItem


def financial_summary(start_date=None, end_date=None):
    query = FinancialEntry.query
    if start_date:
        query = query.filter(FinancialEntry.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(FinancialEntry.created_at <= datetime.combine(end_date, datetime.max.time()))

    entries = query.all()

    pending_receivable = sum(
        float(e.amount or 0) for e in entries if e.status == "pendente" and e.entry_type == "receber"
    )
    pending_payable = sum(
        float(e.amount or 0) for e in entries if e.status == "pendente" and e.entry_type == "pagar"
    )
    paid_in = sum(float(e.amount or 0) for e in entries if e.status == "pago" and e.entry_type == "receber")
    paid_out = sum(float(e.amount or 0) for e in entries if e.status == "pago" and e.entry_type == "pagar")

    overdue_count = sum(1 for e in entries if e.is_overdue)

    return {
        "pending_receivable": pending_receivable,
        "pending_payable": pending_payable,
        "paid_in": paid_in,
        "paid_out": paid_out,
        "cash_balance": paid_in - paid_out,
        "overdue_count": overdue_count,
    }


def cashflow_last_days(days=14):
    start_day = date.today() - timedelta(days=days - 1)
    rows = (
        FinancialEntry.query.filter(FinancialEntry.status == "pago", FinancialEntry.paid_at.isnot(None))
        .filter(FinancialEntry.paid_at >= datetime.combine(start_day, datetime.min.time()))
        .all()
    )

    by_day = defaultdict(lambda: {"in": 0.0, "out": 0.0})
    for entry in rows:
        key = entry.paid_at.date().isoformat()
        if entry.entry_type == "receber":
            by_day[key]["in"] += float(entry.amount or 0)
        else:
            by_day[key]["out"] += float(entry.amount or 0)

    result = []
    for offset in range(days):
        d = start_day + timedelta(days=offset)
        key = d.isoformat()
        result.append(
            {
                "date": key,
                "in": by_day[key]["in"],
                "out": by_day[key]["out"],
                "net": by_day[key]["in"] - by_day[key]["out"],
            }
        )
    return result


def abc_and_replenishment():
    # Valor movimentado por produto em vendas concluidas.
    sales_rows = (
        SalesOrderItem.query.join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
        .filter(SalesOrder.status == "concluido")
        .with_entities(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
            func.coalesce(func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price), 0),
        )
        .group_by(SalesOrderItem.product_id)
        .all()
    )

    totals = {row[0]: {"qty": int(row[1] or 0), "value": float(row[2] or 0)} for row in sales_rows}
    total_value = sum(item["value"] for item in totals.values())

    items = []
    for product in Product.query.order_by(Product.name.asc()).all():
        sold = totals.get(product.id, {"qty": 0, "value": 0.0})
        items.append(
            {
                "product": product,
                "sold_qty": sold["qty"],
                "sold_value": sold["value"],
            }
        )

    items.sort(key=lambda x: x["sold_value"], reverse=True)

    cumulative = 0.0
    suggestions = []
    for row in items:
        share = (row["sold_value"] / total_value) if total_value > 0 else 0.0
        cumulative += share
        if cumulative <= 0.80:
            abc_class = "A"
        elif cumulative <= 0.95:
            abc_class = "B"
        else:
            abc_class = "C"

        product = row["product"]
        # Reposicao simples: alvo = minimo * 2 (ou minimo + 5 para minimo baixo)
        target_stock = max(product.min_stock * 2, product.min_stock + 5)
        suggested_qty = max(target_stock - product.quantity, 0)

        suggestions.append(
            {
                "product": product,
                "abc_class": abc_class,
                "sold_qty": row["sold_qty"],
                "sold_value": row["sold_value"],
                "target_stock": target_stock,
                "suggested_qty": suggested_qty,
                "needs_restock": suggested_qty > 0,
            }
        )

    return suggestions
