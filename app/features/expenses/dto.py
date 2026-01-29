from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List


@dataclass
class ExpenseParticipantDTO:
    username: str
    amount_owed: Decimal


@dataclass(frozen=True)
class ExpenseDTO:
    paid_by: str
    amount: Decimal
    desc: str
    created_at: datetime
    participants: List[ExpenseParticipantDTO] = None
