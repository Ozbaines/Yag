import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, JSON, Boolean, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class DraftStatus(str, enum.Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    edited = "edited"
    published = "published"
    failed = "failed"


class DraftType(str, enum.Enum):
    video = "video"
    image = "image"
    text = "text"
    link = "link"


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_url: Mapped[str] = mapped_column(Text)
    type: Mapped[DraftType] = mapped_column(Enum(DraftType), default=DraftType.video)

    title: Mapped[Optional[str]] = mapped_column(Text)
    original_text: Mapped[Optional[str]] = mapped_column(Text)
    caption: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[str]] = mapped_column(Text)

    media_local_path: Mapped[Optional[str]] = mapped_column(Text)
    media_remote_url: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer)

    virality_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    claude_reasoning: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus), default=DraftStatus.pending_review, index=True)
    admin_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    publications: Mapped[list["Publication"]] = relationship(back_populates="draft", cascade="all, delete-orphan")


class PublicationTarget(str, enum.Enum):
    tg_channel = "tg_channel"
    instagram_reels = "instagram_reels"
    youtube_shorts = "youtube_shorts"


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"), index=True)
    target: Mapped[PublicationTarget] = mapped_column(Enum(PublicationTarget))
    remote_id: Mapped[Optional[str]] = mapped_column(String(255))
    remote_url: Mapped[Optional[str]] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    draft: Mapped[Draft] = relationship(back_populates="publications")


class SubscriberState(str, enum.Enum):
    new = "new"
    warming = "warming"
    paid = "paid"
    churned = "churned"


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64))
    first_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_name: Mapped[Optional[str]] = mapped_column(String(128))
    state: Mapped[SubscriberState] = mapped_column(Enum(SubscriberState), default=SubscriberState.new, index=True)
    drip_step: Mapped[int] = mapped_column(Integer, default=0)
    utm_source: Mapped[Optional[str]] = mapped_column(String(128))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DubDataset(Base):
    """One entry per dubbed video — stores LLM I/O for future fine-tuning."""

    __tablename__ = "dub_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("drafts.id", ondelete="CASCADE"), unique=True, index=True
    )
    source_url: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str] = mapped_column(Text)
    llm_model: Mapped[str] = mapped_column(String(128))

    # Raw text sent to the clip-selection LLM (sampled transcript)
    transcript_input: Mapped[str] = mapped_column(Text)
    # Full JSON response from the LLM (clips, title, caption, hashtags)
    clips_output: Mapped[Optional[dict]] = mapped_column(JSON)
    # [{clip_topic, en_text, ru_text}, ...] — one entry per produced clip
    narrations: Mapped[Optional[list]] = mapped_column(JSON)

    clip_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer)

    # 1 = 👎 Плохо, 2 = 👍 Хорошо, 3 = ⭐ Отлично — NULL until admin rates
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    rated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    provider_payment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subscriber_tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    product_code: Mapped[str] = mapped_column(String(64))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending, index=True)
    raw: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
