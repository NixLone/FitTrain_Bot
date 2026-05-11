from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    tone: Mapped[str] = mapped_column(String(32), default="friendly")
    weekly_goal: Mapped[int] = mapped_column(Integer, default=3)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    workout_types: Mapped[list["WorkoutType"]] = relationship(back_populates="user")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user")
    workout_logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="user")
    measurements: Mapped[list["BodyMeasurement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    plans: Mapped[list["TrainingPlan"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WorkoutType(Base):
    __tablename__ = "workout_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="workout_types")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="workout_type")
    workout_logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="workout_type")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workout_type_id: Mapped[int] = mapped_column(
        ForeignKey("workout_types.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(120))
    message_text: Mapped[str] = mapped_column(Text)
    schedule_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remind_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    specific_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="reminders")
    workout_type: Mapped["WorkoutType"] = relationship(back_populates="reminders")
    weekdays: Mapped[list["ReminderWeekday"]] = relationship(
        back_populates="reminder", cascade="all, delete-orphan"
    )
    events: Mapped[list["ReminderEvent"]] = relationship(
        back_populates="reminder", cascade="all, delete-orphan"
    )


class ReminderWeekday(Base):
    __tablename__ = "reminder_weekdays"
    __table_args__ = (UniqueConstraint("reminder_id", "weekday", name="uq_reminder_weekday"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reminder_id: Mapped[int] = mapped_column(
        ForeignKey("reminders.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(Integer)

    reminder: Mapped["Reminder"] = relationship(back_populates="weekdays")


class ReminderEvent(Base):
    __tablename__ = "reminder_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    reminder_id: Mapped[int] = mapped_column(
        ForeignKey("reminders.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workout_type_id: Mapped[int] = mapped_column(
        ForeignKey("workout_types.id", ondelete="RESTRICT"), index=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    response_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    followup_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evening_check_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reminder: Mapped["Reminder"] = relationship(back_populates="events")


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reminder_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reminder_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workout_type_id: Mapped[int] = mapped_column(
        ForeignKey("workout_types.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    performed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rescheduled_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="workout_logs")
    workout_type: Mapped["WorkoutType"] = relationship(back_populates="workout_logs")


class BodyMeasurement(Base):
    __tablename__ = "body_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="measurements")


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="plans")
    items: Mapped[list["TrainingPlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class TrainingPlanItem(Base):
    __tablename__ = "training_plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("training_plans.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, index=True)
    workout_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workout_types.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[str] = mapped_column(String(32))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plan: Mapped["TrainingPlan"] = relationship(back_populates="items")
