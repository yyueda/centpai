from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ExpenseDTO:
    paid_by: str
    amount: Decimal
    desc: str
    created_at: datetime
