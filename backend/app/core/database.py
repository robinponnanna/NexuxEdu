from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, Text, ForeignKey, DateTime, func, JSON, Boolean, text
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
    current_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    current_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
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

class TrackingSession(Base):
    __tablename__ = "tracking_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    bus_id: Mapped[int] = mapped_column(Integer, ForeignKey("buses.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    active: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)  # SQLite compatible boolean (0/1)
    latest_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latest_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latest_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latest_timestamp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

class BusAssignment(Base):
    __tablename__ = "bus_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bus_id: Mapped[int] = mapped_column(Integer, ForeignKey("buses.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    active: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)  # SQLite compatible boolean (0/1)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# --- Academic Support & Learning Management Models ---

class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(60), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Relationships
    modules: Mapped[List["SubjectModule"]] = relationship("SubjectModule", back_populates="subject", cascade="all, delete-orphan")
    assessments: Mapped[List["Assessment"]] = relationship("Assessment", back_populates="subject", cascade="all, delete-orphan")
    enrollments: Mapped[List["StudentEnrollment"]] = relationship("StudentEnrollment", back_populates="subject", cascade="all, delete-orphan")
    learning_materials: Mapped[List["LearningMaterial"]] = relationship("LearningMaterial", back_populates="subject", cascade="all, delete-orphan")
    micro_lessons: Mapped[List["MicroLesson"]] = relationship("MicroLesson", back_populates="subject", cascade="all, delete-orphan")

class SubjectModule(Base):
    __tablename__ = "subject_modules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    module_number: Mapped[int] = mapped_column(Integer, nullable=False)
    co_code: Mapped[str] = mapped_column(String(10), nullable=False) # e.g. "CO1", "CO2", "CO3", "CO4", "CO5"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", back_populates="modules")
    questions: Mapped[List["AssessmentQuestion"]] = relationship("AssessmentQuestion", back_populates="module")
    learning_materials: Mapped[List["LearningMaterial"]] = relationship("LearningMaterial", back_populates="module")
    micro_lessons: Mapped[List["MicroLesson"]] = relationship("MicroLesson", back_populates="module")

class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False) # 'CA1', 'CA2', 'CA3', 'Midterm', 'Endterm'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    weightage_pct: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    assessment_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", back_populates="assessments")
    questions: Mapped[List["AssessmentQuestion"]] = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    assessment_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subject_modules.id", ondelete="SET NULL"), nullable=True)
    co_code: Mapped[str] = mapped_column(String(10), nullable=False) # e.g. "CO1", "CO2", "CO3"
    question_label: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "Q1", "Q2.a", "Q2.b (OR)"
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    or_group_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True) # group identifier for OR choices

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="questions")
    module: Mapped[Optional["SubjectModule"]] = relationship("SubjectModule", back_populates="questions")
    student_marks: Mapped[List["StudentQuestionMark"]] = relationship("StudentQuestionMark", back_populates="question", cascade="all, delete-orphan")

class StudentQuestionMark(Base):
    __tablename__ = "student_question_marks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    marks_obtained: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_attempted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    student: Mapped["Student"] = relationship("Student")
    question: Mapped["AssessmentQuestion"] = relationship("AssessmentQuestion", back_populates="student_marks")

class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), default="2025-2026", nullable=False)

    # Relationships
    student: Mapped["Student"] = relationship("Student")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="enrollments")

class LearningMaterial(Base):
    __tablename__ = "learning_materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subject_modules.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_reference: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", back_populates="learning_materials")
    module: Mapped[Optional["SubjectModule"]] = relationship("SubjectModule", back_populates="learning_materials")
    pages: Mapped[List["MaterialPage"]] = relationship("MaterialPage", back_populates="material", cascade="all, delete-orphan")
    chunks: Mapped[List["MaterialChunk"]] = relationship("MaterialChunk", back_populates="material", cascade="all, delete-orphan")

class MaterialPage(Base):
    __tablename__ = "material_pages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    page_title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    material: Mapped["LearningMaterial"] = relationship("LearningMaterial", back_populates="pages")
    chunks: Mapped[List["MaterialChunk"]] = relationship("MaterialChunk", back_populates="page", cascade="all, delete-orphan")

class MaterialChunk(Base):
    __tablename__ = "material_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_materials.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("material_pages.id", ondelete="CASCADE"), nullable=True, index=True)
    module_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subject_modules.id", ondelete="SET NULL"), nullable=True)
    co_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    topic_name: Mapped[str] = mapped_column(String(150), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    material: Mapped["LearningMaterial"] = relationship("LearningMaterial", back_populates="chunks")
    page: Mapped[Optional["MaterialPage"]] = relationship("MaterialPage", back_populates="chunks")
    module: Mapped[Optional["SubjectModule"]] = relationship("SubjectModule")

class MicroLesson(Base):
    __tablename__ = "micro_lessons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subject_modules.id", ondelete="SET NULL"), nullable=True)
    co_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    topic_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    scenes_json: Mapped[str] = mapped_column(Text, nullable=False) # JSON array of scene objects
    video_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    video_status: Mapped[Optional[str]] = mapped_column(String(50), default="none", nullable=True) # "ready", "generating", "queued", "failed", "none"
    video_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    video_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_generated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    youtube_resource_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", back_populates="micro_lessons")
    module: Mapped[Optional["SubjectModule"]] = relationship("SubjectModule", back_populates="micro_lessons")

# Database Engine & Session
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe column addition for micro_lessons if table already existed without new columns
        for col_def in [
            "video_path VARCHAR(255)",
            "video_status VARCHAR(50) DEFAULT 'none'",
            "video_duration INTEGER",
            "video_content_hash VARCHAR(64)",
            "video_error TEXT",
            "video_generated_at DATETIME",
            "audio_path VARCHAR(255)",
            "youtube_resource_json TEXT"
        ]:
            col_name = col_def.split()[0]
            try:
                await conn.execute(text(f"ALTER TABLE micro_lessons ADD COLUMN {col_def};"))
            except Exception:
                pass

async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
