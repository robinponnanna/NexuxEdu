from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, Text, ForeignKey, DateTime, func, JSON, Boolean, UniqueConstraint, Index
from typing import Optional, List
import datetime
from app.core.config import settings
from app.core.datetime_utils import utcnow

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False) # 'student', 'faculty', 'parent', 'admin'
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class Bus(Base):
    __tablename__ = "buses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bus_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    route_name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    current_lat: Mapped[float] = mapped_column(Float, default=28.613939)
    current_lng: Mapped[float] = mapped_column(Float, default=77.209021)
    speed_kmh: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="Active") # 'Active', 'Congested', 'Depot'
    stops_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of stops
    waypoints_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of [lat, lng]
    last_updated: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class Parent(Base):
    __tablename__ = "parents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    emp_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(60), nullable=False)
    designation: Mapped[str] = mapped_column(String(60), nullable=False)
    annual_salary: Mapped[float] = mapped_column(Float, nullable=False) # Sensitive RBAC field

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("parents.id", ondelete="SET NULL"), nullable=True)
    bus_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("buses.id", ondelete="SET NULL"), nullable=True)
    roll_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(60), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(10), default="Section A", nullable=False)

class Attendance(Base):
    __tablename__ = "attendance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(60), nullable=False)
    total_classes: Mapped[int] = mapped_column(Integer, default=40)
    attended_classes: Mapped[int] = mapped_column(Integer, nullable=False)
    attendance_pct: Mapped[float] = mapped_column(Float, nullable=False)

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_roles: Mapped[str] = mapped_column(String(255), nullable=False) # comma-separated list of roles e.g. "student,faculty,parent,admin"
    department: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # serialized vector for cosine similarity

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False) # e.g. 'EVENT_PRIVILEGE_PROBE', 'UNAUTHORIZED_QUERY'
    details: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)

    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    clash_cases = relationship("ClashCase", back_populates="event", cascade="all, delete-orphan")

class EventParticipant(Base):
    __tablename__ = "event_participants"
    __table_args__ = (
        UniqueConstraint("event_id", "student_id", name="uq_event_student"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)

    event = relationship("Event", back_populates="participants")
    student = relationship("Student")

class CourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        UniqueConstraint("course_code", "section", "semester", name="uq_offering_section_sem"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_code: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    section: Mapped[str] = mapped_column(String(20), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[str] = mapped_column(String(60), nullable=False)
    faculty_id: Mapped[int] = mapped_column(Integer, ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False)

    faculty = relationship("Faculty")
    assessments = relationship("Assessment", back_populates="offering", cascade="all, delete-orphan")

class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    offering_id: Mapped[int] = mapped_column(Integer, ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "midterm", "lab_midterm", "class_test"
    start_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    offering = relationship("CourseOffering", back_populates="assessments")

class ClashCase(Base):
    __tablename__ = "clash_cases"
    __table_args__ = (
        UniqueConstraint("event_id", "student_id", "assessment_id", name="uq_case_event_student_assessment"),
        Index("ix_clash_cases_status", "status"),
        Index("ix_clash_cases_student_id", "student_id"),
        Index("ix_clash_cases_assessment_id", "assessment_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    assessment_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DETECTED")
    
    suggested_retake_assessment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)
    retake_assessment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)
    retake_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    retake_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    filed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    decided_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    event = relationship("Event", back_populates="clash_cases")
    student = relationship("Student")
    assessment = relationship("Assessment", foreign_keys=[assessment_id])
    suggested_retake = relationship("Assessment", foreign_keys=[suggested_retake_assessment_id])
    retake_assessment = relationship("Assessment", foreign_keys=[retake_assessment_id])
    timeline = relationship("CaseTimeline", back_populates="clash_case", cascade="all, delete-orphan", order_by="CaseTimeline.at.asc()")

class CaseTimeline(Base):
    __tablename__ = "case_timelines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("clash_cases.id", ondelete="CASCADE"), nullable=False)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_role: Mapped[str] = mapped_column(String(30), nullable=False) # "admin", "faculty", "student", "SYSTEM"
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)

    clash_case = relationship("ClashCase", back_populates="timeline")

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    case_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("clash_cases.id", ondelete="SET NULL"), nullable=True)
    event_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)

# Database Engine & Session
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
