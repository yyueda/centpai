from decimal import Decimal
from app.features.expenses.algorithms.simplify_debts import simplify_debts


def test_no_balances_returns_empty():
    assert simplify_debts([]) == []


def test_all_negative_returns_empty():
    # No creditors, nothing to settle
    assert simplify_debts([("alice", Decimal("-10")), ("bob", Decimal("-5"))]) == []


def test_all_zero_returns_empty():
    assert simplify_debts([("alice", Decimal("0")), ("bob", Decimal("0"))]) == []


def test_decimal_precision_one_cent():
    balances = [("alice", Decimal("-0.01")), ("bob", Decimal("0.01"))]
    result = simplify_debts(balances)
    assert len(result) == 1
    assert result[0][2] == Decimal("0.01")


def test_complex_group_settlement():
    # 4 people, mixed debts and credits
    balances = [
        ("alice", Decimal("-40.00")),
        ("bob", Decimal("-10.00")),
        ("charlie", Decimal("25.00")),
        ("diana", Decimal("25.00")),
    ]
    result = simplify_debts(balances)
    total = sum(a for _, _, a in result)
    assert total == Decimal("50.00")
