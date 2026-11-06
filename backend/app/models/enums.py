from enum import Enum


class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class BillingPlan(str, Enum):
    BOOKING_FEE = "booking_fee"
    SUBSCRIPTION = "subscription"


class ChargeKind(str, Enum):
    BOOKING_FEE = "booking_fee"
    SUBSCRIPTION = "subscription"


class ChargeStatus(str, Enum):
    OWED = "owed"
    PAID = "paid"
    WAIVED = "waived"


class AppointmentStatus(str, Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
