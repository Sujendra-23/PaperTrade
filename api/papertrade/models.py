from typing import Literal

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    account_id: str | None = Field(default=None, min_length=1, max_length=80)
    symbol: str = Field(min_length=1, max_length=10, pattern=r"^[A-Z]+$")
    side: Literal["BUY", "SELL"]
    kind: Literal["LIMIT", "MARKET"] = "LIMIT"
    quantity: int = Field(gt=0, le=1_000_000, strict=True)
    price: int | None = Field(default=None, gt=0, le=1_000_000_000, strict=True)


class AccountRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
