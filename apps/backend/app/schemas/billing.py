from typing import Literal

from pydantic import BaseModel, EmailStr


class CheckoutRequest(BaseModel):
    tier: Literal["starter", "pro"]
    email: EmailStr


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str
