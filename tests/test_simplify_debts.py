from decimal import Decimal
from app.features.expenses.algorithms.simplify_debts import simplify_debts


def test_no_balances_returns_empty():
    assert simplify_debts([]) == []


def test_all_positive_returns_empty():
    # No debtors, nothing to settle
    assert simplify_debts([("alice", Decimal("10")), ("bob", Decimal("5"))]) == []


def test_simple_debt():
    balances = [("alice", Decimal("-10.00")), ("bob", Decimal("10.00"))]
    result = simplify_debts(balances)
    assert result == [("alice", "bob", Decimal("10.00"))]


def test_debt_splits_across_creditors():
    balances = [
        ("alice", Decimal("-10.00")),
        ("bob", Decimal("5.00")),
        ("carol", Decimal("5.00")),
    ]
    result = simplify_debts(balances)
    total_paid = sum(a for _, _, a in result)
    assert total_paid == Decimal("10.00")
