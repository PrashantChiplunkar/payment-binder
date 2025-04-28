from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, Type
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    """Authentication methods supported by API clients."""
    BASIC = "Basic"
    BEARER = "Bearer"
    API_KEY = "ApiKey"  # For future providers that might use API keys


class APIResponse(BaseModel):
    """Standardized API response model."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class PaymentProviderType(str, Enum):
    """Supported payment providers."""
    PADDLE = "paddle"
    RAZORPAY = "razorpay"
    # Easy to add more providers here in the future


class TransactionStatus(str, Enum):
    """Standardized transaction statuses across providers."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class BillingCycle(str, Enum):
    """Standardized billing cycles across providers."""
    DAILY = "day"
    WEEKLY = "week"
    MONTHLY = "month"
    YEARLY = "year"


class SubscriptionDetails(BaseModel):
    """Standardized subscription details."""
    id: str
    status: str
    created_at: datetime
    next_billing_date: Optional[datetime] = None
    plan_id: str
    customer_id: str


class TransactionDetails(BaseModel):
    """Standardized transaction details."""
    id: str
    status: TransactionStatus
    amount: float
    currency: str
    created_at: datetime
    invoice_url: Optional[str] = None
