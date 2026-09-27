from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, Text, ForeignKey, DateTime, func, JSON
from typing import Optional, List
import datetime
from app.core.config import settings

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
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# Database Engine & Session
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
