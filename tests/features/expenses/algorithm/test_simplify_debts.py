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


def test_all_negative_returns_empty():
    # No creditors, nothing to settle
    assert simplify_debts([("alice", Decimal("-10")), ("bob", Decimal("-5"))]) == []


def test_all_zero_returns_empty():
    assert simplify_debts([("alice", Decimal("0")), ("bob", Decimal("0"))]) == []


def test_single_zero_balance_returns_empty():
    assert simplify_debts([("alice", Decimal("0"))]) == []


def test_amounts_are_positive():
    balances = [("alice", Decimal("-15.00")), ("bob", Decimal("15.00"))]
    result = simplify_debts(balances)
    for _, _, amount in result:
        assert amount > Decimal("0")


def test_no_self_payments():
    balances = [("alice", Decimal("-10.00")), ("bob", Decimal("10.00"))]
    result = simplify_debts(balances)
    for from_user, to_user, _ in result:
        assert from_user != to_user


def test_returns_list_of_tuples():
    balances = [("alice", Decimal("-5.00")), ("bob", Decimal("5.00"))]
    result = simplify_debts(balances)
    assert isinstance(result, list)
    assert all(isinstance(r, tuple) and len(r) == 3 for r in result)


def test_multiple_debtors_one_creditor():
    balances = [
        ("alice", Decimal("-10.00")),
        ("bob", Decimal("-20.00")),
        ("charlie", Decimal("30.00")),
    ]
    result = simplify_debts(balances)
    total = sum(a for _, _, a in result)
    assert total == Decimal("30.00")
    for _, to_user, _ in result:
        assert to_user == "charlie"


def test_one_debtor_multiple_creditors():
    balances = [
        ("alice", Decimal("-30.00")),
        ("bob", Decimal("10.00")),
        ("charlie", Decimal("20.00")),
    ]
    result = simplify_debts(balances)
    total = sum(a for _, _, a in result)
    assert total == Decimal("30.00")
    for from_user, _, _ in result:
        assert from_user == "alice"


def test_decimal_precision_one_cent():
    balances = [("alice", Decimal("-0.01")), ("bob", Decimal("0.01"))]
    result = simplify_debts(balances)
    assert len(result) == 1
    assert result[0][2] == Decimal("0.01")


def test_total_payments_equal_total_debt():
    balances = [
        ("alice", Decimal("-50.00")),
        ("bob", Decimal("20.00")),
        ("charlie", Decimal("30.00")),
    ]
    result = simplify_debts(balances)
    total_debt = sum(abs(b) for _, b in balances if b < 0)
    total_paid = sum(a for _, _, a in result)
    assert total_paid == total_debt


def test_large_equal_split():
    balances = [
        ("alice", Decimal("-100.00")),
        ("bob", Decimal("50.00")),
        ("charlie", Decimal("50.00")),
    ]
    result = simplify_debts(balances)
    total = sum(a for _, _, a in result)
    assert total == Decimal("100.00")


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


def test_from_user_is_always_debtor():
    balances = [
        ("alice", Decimal("-20.00")),
        ("bob", Decimal("20.00")),
    ]
    result = simplify_debts(balances)
    from_users = {r[0] for r in result}
    assert from_users == {"alice"}


def test_to_user_is_always_creditor():
    balances = [
        ("alice", Decimal("-20.00")),
        ("bob", Decimal("20.00")),
    ]
    result = simplify_debts(balances)
    to_users = {r[1] for r in result}
    assert to_users == {"bob"}


def test_large_amount():
    balances = [
        ("alice", Decimal("-9999.99")),
        ("bob", Decimal("9999.99")),
    ]
    result = simplify_debts(balances)
    assert len(result) == 1
    assert result[0][2] == Decimal("9999.99")
