from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SELLER = "SELLER" 
    CUSTOMER = "CUSTOMER"


class PaymentProvider(str, Enum):
    STRIPE = "STRIPE"
    MOCK = "MOCK"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"