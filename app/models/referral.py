from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE / REVOKED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class PartnerInvite(Base):
    """Admin-generated codes. The ONLY way to become a partner."""
    __tablename__ = "partner_invites"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    note = Column(String, nullable=True)  # admin label, e.g. "CSC201 rep"
    created_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    used_by = relationship("User", foreign_keys=[used_by_user_id])


class CoinEntry(Base):
    """Signed ledger. Balance = SUM(amount). 1 coin = 1 naira."""
    __tablename__ = "coin_ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # + earn, - spend
    type = Column(String, nullable=False)  # REFERRAL_REWARD / CHECKOUT_SPEND / HOLD_REFUND / BONUS
    reference = Column(String, nullable=True)  # payment reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PartnerEarning(Base):
    """5% cash entries per referred payment. Immutable history."""
    __tablename__ = "partner_earnings"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    source_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payment_reference = Column(String, nullable=False)
    amount_naira = Column(Integer, nullable=False)
    available_at = Column(DateTime(timezone=True), nullable=False)  # created + 7 days
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PayoutRequest(Base):
    __tablename__ = "payout_requests"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    amount_naira = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="PENDING")  # PENDING / PAID / REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)