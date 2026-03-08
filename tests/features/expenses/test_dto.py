import pytest
from decimal import Decimal
from datetime import datetime
from app.features.expenses.dto import (
    ExpenseParticipantDTO,
    ExpenseDTO,
    BalanceDTO,
    SimplifiedDebtDTO,
)


class TestExpenseParticipantDTO:
    def test_creation(self):
        dto = ExpenseParticipantDTO(username="alice", amount_owed=Decimal("10.00"))
        assert dto.username == "alice"
        assert dto.amount_owed == Decimal("10.00")

    def test_immutable(self):
        dto = ExpenseParticipantDTO(username="alice", amount_owed=Decimal("10.00"))
        with pytest.raises(Exception):
            dto.username = "bob"  # type: ignore


class TestExpenseDTO:
    def test_creation_without_participants(self):
        now = datetime.now()
        dto = ExpenseDTO(
            id=1,
            paid_by="alice",
            amount=Decimal("50.00"),
            desc="Dinner",
            created_at=now,
        )
        assert dto.id == 1
        assert dto.paid_by == "alice"
        assert dto.amount == Decimal("50.00")
        assert dto.desc == "Dinner"
        assert dto.created_at == now
        assert dto.participants is None

    def test_creation_with_participants(self):
        now = datetime.now()
        participants = [
            ExpenseParticipantDTO(username="bob", amount_owed=Decimal("25.00")),
            ExpenseParticipantDTO(username="charlie", amount_owed=Decimal("25.00")),
        ]
        dto = ExpenseDTO(
            id=2,
            paid_by="alice",
            amount=Decimal("50.00"),
            desc="Lunch",
            created_at=now,
            participants=participants,
        )
        assert len(dto.participants) == 2
        assert dto.participants[0].username == "bob"

    def test_immutable(self):
        now = datetime.now()
        dto = ExpenseDTO(
            id=1, paid_by="alice", amount=Decimal("50.00"), desc="x", created_at=now
        )
        with pytest.raises(Exception):
            dto.id = 2  # type: ignore


class TestBalanceDTO:
    def test_creation(self):
        dto = BalanceDTO(username="alice", balance=Decimal("15.50"))
        assert dto.username == "alice"
        assert dto.balance == Decimal("15.50")

    def test_negative_balance(self):
        dto = BalanceDTO(username="bob", balance=Decimal("-10.00"))
        assert dto.balance == Decimal("-10.00")

    def test_zero_balance(self):
        dto = BalanceDTO(username="charlie", balance=Decimal("0.00"))
        assert dto.balance == Decimal("0.00")

    def test_immutable(self):
        dto = BalanceDTO(username="alice", balance=Decimal("5.00"))
        with pytest.raises(Exception):
            dto.username = "bob"  # type: ignore


class TestSimplifiedDebtDTO:
    def test_creation(self):
        dto = SimplifiedDebtDTO(
            from_user="alice", to_user="bob", amount=Decimal("20.00")
        )
        assert dto.from_user == "alice"
        assert dto.to_user == "bob"
        assert dto.amount == Decimal("20.00")

    def test_immutable(self):
        dto = SimplifiedDebtDTO(
            from_user="alice", to_user="bob", amount=Decimal("20.00")
        )
        with pytest.raises(Exception):
            dto.from_user = "charlie"  # type: ignore
