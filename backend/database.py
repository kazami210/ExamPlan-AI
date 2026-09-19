from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, Date, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=False, default="Khách vãng lai")
    avatar_url = Column(String(500), nullable=True)
    provider = Column(String(50), default="guest") # "google", "facebook", "guest"
    provider_id = Column(String(255), nullable=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    is_guest = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_saved_permanently = Column(Boolean, default=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False) # pdf, docx, txt, url
    file_path = Column(String(500), nullable=True)
    extracted_text = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    subject_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="documents")
    topics = relationship("SubjectTopic", back_populates="document", cascade="all, delete-orphan")
    plans = relationship("StudyPlan", back_populates="document", cascade="all, delete-orphan")

class SubjectTopic(Base):
    __tablename__ = "subject_topics"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    topic_code = Column(String(50), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(String(50), default="Trung bình") # Dễ, Trung bình, Khó
    estimated_hours = Column(Float, default=2.0)
    importance_score = Column(Float, default=8.0) # 1 - 10
    order_index = Column(Integer, default=0)

    document = relationship("Document", back_populates="topics")

class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    title = Column(String(255), nullable=False)
    subject_name = Column(String(255), nullable=False)
    target_score = Column(Float, default=8.0) # 5.0 -> 10.0
    exam_date = Column(Date, nullable=False)
    daily_hours = Column(Float, default=2.0)
    total_days = Column(Integer, default=14)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="plans")
    document = relationship("Document", back_populates="plans")
    tasks = relationship("StudyTask", back_populates="plan", cascade="all, delete-orphan", order_by="StudyTask.study_date, StudyTask.order_index")

class StudyTask(Base):
    __tablename__ = "study_tasks"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False)
    study_date = Column(Date, nullable=False)
    day_number = Column(Integer, default=1)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), default="study_new") # study_new, spaced_review, practice_exam, final_review
    topic_title = Column(String(255), nullable=True)
    difficulty = Column(String(50), default="Trung bình")
    estimated_minutes = Column(Integer, default=60)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    order_index = Column(Integer, default=0)
    # Cached AI-generated lesson & quiz data (JSON string) to avoid redundant Gemini API calls
    lesson_data_basic = Column(Text, nullable=True)
    lesson_data_advanced = Column(Text, nullable=True)
    image_urls = Column(Text, nullable=True) # JSON list of image/slide URLs or paths specifically for this task scope
    start_page = Column(Integer, nullable=True) # e.g. 1
    end_page = Column(Integer, nullable=True) # e.g. 3
    slide_scope = Column(String(100), nullable=True) # e.g. "Slide 1 - 3"

    plan = relationship("StudyPlan", back_populates="tasks")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    role = Column(String(50), nullable=False) # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Safe auto-migration for existing SQLite / Postgres tables
    try:
        with engine.connect() as conn:
            for col, col_type in [
                ("lesson_data_basic", "TEXT"),
                ("lesson_data_advanced", "TEXT"),
                ("image_urls", "TEXT"),
                ("start_page", "INTEGER"),
                ("end_page", "INTEGER"),
                ("slide_scope", "TEXT")
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE study_tasks ADD COLUMN {col} {col_type};"))
                    conn.commit()
                except Exception:
                    pass
    except Exception:
        pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
