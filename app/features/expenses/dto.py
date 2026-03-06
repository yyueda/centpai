from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List


@dataclass(frozen=True)
class ExpenseParticipantDTO:
    username: str
    amount_owed: Decimal

@dataclass(frozen=True)
class ExpenseDTO:
    id: int
    paid_by: str
    amount: Decimal
    desc: str
    created_at: datetime
    participants: List[ExpenseParticipantDTO] | None = None

@dataclass(frozen=True)
class BalanceDTO:
    username: str
    balance: Decimal

@dataclass(frozen=True)
class SimplifiedDebtDTO:
    from_user: str
    to_user: str
    amount: Decimal
