from datetime import datetime, date
from typing import Optional, List, Dict
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db, Document, SubjectTopic, StudyPlan, StudyTask, ChatMessage, User
import secrets
from fastapi import Header
from backend.services.parsers import extract_document_content, parse_url
from backend.services.ai_service import ai_service
from backend.services.scheduler import scheduler
from backend.services.timetable_service import timetable_service
from backend.services.rag_service import chunk_text, search_relevant_chunks
from backend.config import UPLOAD_DIR, get_google_client_id
import base64
import json
import httpx

router = APIRouter(prefix="/api")

# --- Authentication Schemas & Helper ---
class GoogleAuthRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    google_id: Optional[str] = None
    guest_token: Optional[str] = None
    credential: Optional[str] = None

class FacebookAuthRequest(BaseModel):
    email: Optional[str] = None
    name: str
    avatar_url: Optional[str] = None
    facebook_id: Optional[str] = None
    guest_token: Optional[str] = None

class UpgradeGuestRequest(BaseModel):
    guest_token: str

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    return db.query(User).filter(User.session_token == token).first()

def migrate_guest_data(guest_token: str, real_user: User, db: Session):
    """Transfers all documents, topics, and plans from a guest session to the permanent user."""
    if not guest_token:
        return
    guest = db.query(User).filter(User.session_token == guest_token, User.is_guest == True).first()
    if guest and guest.id != real_user.id:
        docs = db.query(Document).filter(Document.user_id == guest.id).all()
        for d in docs:
            d.user_id = real_user.id
            d.is_saved_permanently = True
        plans = db.query(StudyPlan).filter(StudyPlan.user_id == guest.id).all()
        for p in plans:
            p.user_id = real_user.id
        guest.session_token = f"migrated_{guest.id}_{secrets.token_hex(4)}"
        db.commit()

def parse_image_urls(val) -> List[str]:
    """Safely parse image_urls stored as JSON or string list."""
    if not val:
        return []
    if isinstance(val, list):
        return [str(x) for x in val if x]
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return [str(x) for x in parsed if x]
    except Exception:
        pass
    cleaned = []
    for item in str(val).replace("\r", "").replace(",", "\n").split("\n"):
        item_str = item.strip()
        if item_str:
            cleaned.append(item_str)
    return cleaned

def find_available_slides(task_title: str, topic_title: str = "", task_id: int = None) -> List[str]:
    """
    Automatically discovers and matches available slides from static repositories
    (frontend/slides and data/uploads/slides) based on:
    1. Chapter number extracted from task_title or topic_title (e.g. 'Chương 5' -> chuong_5_*.svg/jpg/png)
    2. Task ID matching (e.g. task_{task_id}_*)
    3. Topic keywords matching
    """
    import re
    search_dirs = [
        Path(__file__).resolve().parent.parent / "frontend" / "slides",
        UPLOAD_DIR / "slides"
    ]
    
    # Extract chapter number if present
    full_text = f"{task_title} {topic_title}".lower()
    ch_match = re.search(r"(?:chương|chuong|ch|bài|bai)\s*(\d+)", full_text)
    ch_num = ch_match.group(1) if ch_match else None

    discovered = []
    seen_names = set()

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        # 1. Look for chapter files if chapter number found (e.g. chuong_5_1.svg, chuong_5_2.jpg...)
        if ch_num:
            patterns = [
                f"*chuong_{ch_num}_*.*",
                f"*chuong{ch_num}_*.*",
                f"*ch_{ch_num}_*.*",
                f"*ch{ch_num}_*.*",
                f"chuong_{ch_num}.*",
                f"ch_{ch_num}.*"
            ]
            for pat in patterns:
                for f in sorted(s_dir.glob(pat)):
                    if f.suffix.lower() in [".svg", ".png", ".jpg", ".jpeg", ".webp"]:
                        if f.name not in seen_names:
                            seen_names.add(f.name)
                            discovered.append(f"/static/slides/{f.name}")

        # 2. Look for task id files (e.g. task_12_*.svg/jpg...)
        if task_id:
            for f in sorted(s_dir.glob(f"*task_{task_id}_*.*")):
                if f.suffix.lower() in [".svg", ".png", ".jpg", ".jpeg", ".webp"]:
                    if f.name not in seen_names:
                        seen_names.add(f.name)
                        discovered.append(f"/static/slides/{f.name}")

    # Fallback to general slides if none found and it's a known philosophy / physics topic
    if not discovered and ch_num:
        alt_name = f"slide_triet_hoc_{ch_num}.svg"
        for s_dir in search_dirs:
            if (s_dir / alt_name).exists():
                discovered.append(f"/static/slides/{alt_name}")
                break

    return discovered

def partition_chapter_slides_for_tasks(tasks_for_chapter: List[Dict], all_chapter_slides: List[str]):
    """
    Intelligently partitions chapter slides across tasks based on the number of sessions
    and task types, assigning strictly scoped slide subsets with start_page, end_page, and slide_scope.
    """
    total_slides = len(all_chapter_slides)
    if total_slides == 0:
        for t in tasks_for_chapter:
            t["start_page"] = None
            t["end_page"] = None
            t["slide_scope"] = None
            t["image_urls"] = []
        return

    # Separate learning sessions vs review sessions
    primary_tasks = [t for t in tasks_for_chapter if t.get("task_type") == "study_new"]
    review_tasks = [t for t in tasks_for_chapter if t.get("task_type") == "spaced_review"]
    other_tasks = [t for t in tasks_for_chapter if t.get("task_type") not in ["study_new", "spaced_review"]]

    num_primary = len(primary_tasks)

    if num_primary <= 1:
        for t in primary_tasks:
            t["start_page"] = 1
            t["end_page"] = total_slides
            t["slide_scope"] = f"Slide 1 - {total_slides} (Toàn bộ chương)" if total_slides > 1 else "Slide 1 (Trọn vẹn)"
            t["image_urls"] = list(all_chapter_slides)
    else:
        chunk_size = max(1, (total_slides + num_primary - 1) // num_primary)
        for idx, t in enumerate(primary_tasks):
            start_idx = idx * chunk_size
            end_idx = min(total_slides, (idx + 1) * chunk_size)
            if start_idx >= total_slides:
                start_idx = total_slides - 1
                end_idx = total_slides

            scoped_slides = all_chapter_slides[start_idx:end_idx]
            s_num = start_idx + 1
            e_num = end_idx
            if s_num == e_num:
                t["slide_scope"] = f"Slide {s_num} (Phần {idx + 1}/{num_primary})"
            else:
                t["slide_scope"] = f"Slide {s_num} - {e_num} (Phần {idx + 1}/{num_primary})"
            t["start_page"] = s_num
            t["end_page"] = e_num
            t["image_urls"] = scoped_slides

    # Review tasks: Focus strictly on key synthesis slides
    for r_idx, t in enumerate(review_tasks):
        rev_start = max(0, total_slides - 2) if total_slides >= 2 else 0
        rev_slides = all_chapter_slides[rev_start:]
        t["start_page"] = rev_start + 1
        t["end_page"] = total_slides
        t["slide_scope"] = f"Slide {rev_start + 1} - {total_slides} (Trọng tâm ôn tập)" if len(rev_slides) > 1 else f"Slide {total_slides} (Trọng tâm ôn tập)"
        t["image_urls"] = rev_slides

    # Final review / practice exam tasks
    for t in other_tasks:
        t["start_page"] = None
        t["end_page"] = None
        t["slide_scope"] = None
        t["image_urls"] = []

def assign_plan_task_scopes(plan_id: int, db: Session):
    """
    Computes and persists scoped slide ranges (start_page, end_page, slide_scope, image_urls)
    for all tasks in a plan.
    Prioritizes real extracted slides/pages from the uploaded document (PDF/PPTX) over mock SVGs.
    """
    import re
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    tasks = db.query(StudyTask).filter(StudyTask.plan_id == plan_id).order_by(StudyTask.study_date, StudyTask.order_index).all()
    if not tasks:
        return

    doc = db.query(Document).filter(Document.id == plan.document_id).first() if plan else None
    doc_slides = []
    if doc and doc.document_images:
        try:
            parsed = json.loads(doc.document_images)
            if isinstance(parsed, list) and len(parsed) > 0:
                doc_slides = parsed
        except Exception:
            pass

    # If the document has real extracted slides/pages (e.g. authentic PDF pages)
    if doc_slides:
        def get_ch_key_real(t):
            full_text = f"{t.title} {t.topic_title or ''}".lower()
            m = re.search(r"(?:chương|chuong|ch|bài|bai)\s*(\d+)", full_text)
            return f"ch_{m.group(1)}" if m else (t.topic_title or "general")

        groups = {}
        for t in tasks:
            groups.setdefault(get_ch_key_real(t), []).append(t)

        # If document covers a single chapter or all tasks belong to this document
        if len(groups) == 1 or len(doc_slides) > 0:
            # If all tasks are in 1 group (like Chapter 5 PDF), partition all real slides across these tasks
            if len(groups) == 1:
                group_tasks = list(groups.values())[0]
                task_dicts = [{"task_type": t.task_type, "title": t.title, "topic_title": t.topic_title} for t in group_tasks]
                partition_chapter_slides_for_tasks(task_dicts, doc_slides)
                for t_orm, t_dict in zip(group_tasks, task_dicts):
                    t_orm.start_page = t_dict.get("start_page")
                    t_orm.end_page = t_dict.get("end_page")
                    t_orm.slide_scope = t_dict.get("slide_scope")
                    t_orm.image_urls = json.dumps(t_dict.get("image_urls", []), ensure_ascii=False) if t_dict.get("image_urls") else None
            else:
                # Multiple chapters: distribute doc_slides proportionally across chapters or use chapter matching
                total_chapters = len(groups)
                slides_per_chapter = max(1, len(doc_slides) // total_chapters)
                for ch_idx, (key, task_group) in enumerate(groups.items()):
                    ch_start = ch_idx * slides_per_chapter
                    ch_end = len(doc_slides) if ch_idx == total_chapters - 1 else min(len(doc_slides), (ch_idx + 1) * slides_per_chapter)
                    ch_slides = doc_slides[ch_start:ch_end]
                    task_dicts = [{"task_type": t.task_type, "title": t.title, "topic_title": t.topic_title} for t in task_group]
                    partition_chapter_slides_for_tasks(task_dicts, ch_slides)
                    for t_orm, t_dict in zip(task_group, task_dicts):
                        t_orm.start_page = t_dict.get("start_page")
                        t_orm.end_page = t_dict.get("end_page")
                        t_orm.slide_scope = t_dict.get("slide_scope")
                        t_orm.image_urls = json.dumps(t_dict.get("image_urls", []), ensure_ascii=False) if t_dict.get("image_urls") else None
        try:
            db.commit()
        except Exception:
            db.rollback()
        return

    # Fallback to matching static slides (e.g. for sample syllabi or mock SVGs)
    def get_ch_key(t):
        full_text = f"{t.title} {t.topic_title or ''}".lower()
        m = re.search(r"(?:chương|chuong|ch|bài|bai)\s*(\d+)", full_text)
        return f"ch_{m.group(1)}" if m else (t.topic_title or "general")

    groups = {}
    for t in tasks:
        groups.setdefault(get_ch_key(t), []).append(t)

    for key, task_group in groups.items():
        sample = task_group[0]
        all_slides = find_available_slides(sample.title, sample.topic_title or "", None)
        
        task_dicts = [{"task_type": t.task_type, "title": t.title, "topic_title": t.topic_title} for t in task_group]
        partition_chapter_slides_for_tasks(task_dicts, all_slides)

        for t_orm, t_dict in zip(task_group, task_dicts):
            t_orm.start_page = t_dict.get("start_page")
            t_orm.end_page = t_dict.get("end_page")
            t_orm.slide_scope = t_dict.get("slide_scope")
            t_orm.image_urls = json.dumps(t_dict.get("image_urls", []), ensure_ascii=False) if t_dict.get("image_urls") else None

    try:
        db.commit()
    except Exception:
        db.rollback()

# --- Auth Endpoints ---

@router.get("/config")
def get_public_config():
    return {
        "google_client_id": get_google_client_id()
    }

@router.post("/auth/google")
async def login_google(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    email = req.email
    name = req.name
    avatar_url = req.avatar_url
    google_id = req.google_id

    # If ID token credential is sent from Google Identity Services SDK
    if req.credential:
        payload = None
        # 1. Try Google TokenInfo endpoint
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={req.credential}")
                if res.status_code == 200:
                    payload = res.json()
        except Exception as e:
            print(f"[Google Auth] Tokeninfo API call note: {e}")

        # 2. Fallback to decoding JWT payload if offline or mock
        if not payload:
            try:
                parts = req.credential.split(".")
                if len(parts) >= 2:
                    padding = "=" * (4 - len(parts[1]) % 4)
                    payload_bytes = base64.urlsafe_b64decode(parts[1] + padding)
                    payload = json.loads(payload_bytes.decode("utf-8"))
            except Exception as e:
                print(f"[Google Auth] JWT decode error: {e}")

        if payload:
            email = payload.get("email", email)
            name = payload.get("name", name or (email.split("@")[0] if email else "Google User"))
            avatar_url = payload.get("picture", avatar_url)
            google_id = payload.get("sub", google_id)

    if not email:
        raise HTTPException(status_code=400, detail="Không thể xác thực thông tin tài khoản Google.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=name or email.split("@")[0],
            avatar_url=avatar_url or f"https://api.dicebear.com/7.x/initials/svg?seed={name or email}",
            provider="google",
            provider_id=google_id,
            session_token=secrets.token_hex(24),
            is_guest=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.full_name = name or user.full_name
        if avatar_url:
            user.avatar_url = avatar_url
        user.is_guest = False
        db.commit()

    if req.guest_token:
        migrate_guest_data(req.guest_token, user, db)

    return {
        "success": True,
        "token": user.session_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "avatar_url": user.avatar_url,
            "provider": user.provider,
            "is_guest": False
        }
    }

@router.post("/auth/facebook")
def login_facebook(req: FacebookAuthRequest, db: Session = Depends(get_db)):
    user = None
    if req.email:
        user = db.query(User).filter(User.email == req.email).first()
    if not user and req.facebook_id:
        user = db.query(User).filter(User.provider == "facebook", User.provider_id == req.facebook_id).first()

    if not user:
        user = User(
            email=req.email,
            full_name=req.name,
            avatar_url=req.avatar_url or f"https://api.dicebear.com/7.x/initials/svg?seed={req.name}",
            provider="facebook",
            provider_id=req.facebook_id,
            session_token=secrets.token_hex(24),
            is_guest=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.full_name = req.name or user.full_name
        if req.avatar_url:
            user.avatar_url = req.avatar_url
        user.is_guest = False
        db.commit()

    if req.guest_token:
        migrate_guest_data(req.guest_token, user, db)

    return {
        "success": True,
        "token": user.session_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "avatar_url": user.avatar_url,
            "provider": user.provider,
            "is_guest": False
        }
    }

@router.post("/auth/guest")
def login_guest(db: Session = Depends(get_db)):
    guest_token = secrets.token_hex(24)
    guest = User(
        full_name="Khách Vãng Lai",
        email=None,
        avatar_url="https://api.dicebear.com/7.x/bottts/svg?seed=guest",
        provider="guest",
        session_token=guest_token,
        is_guest=True
    )
    db.add(guest)
    db.commit()
    db.refresh(guest)
    return {
        "success": True,
        "token": guest.session_token,
        "user": {
            "id": guest.id,
            "email": None,
            "name": guest.full_name,
            "avatar_url": guest.avatar_url,
            "provider": "guest",
            "is_guest": True
        }
    }

@router.get("/auth/me")
def get_me(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    if not user:
        raise HTTPException(status_code=401, detail="Phiên làm việc không hợp lệ.")
    return {
        "success": True,
        "token": user.session_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "avatar_url": user.avatar_url,
            "provider": user.provider,
            "is_guest": user.is_guest
        }
    }

@router.post("/auth/upgrade-guest")
def upgrade_guest(req: UpgradeGuestRequest, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    real_user = get_current_user(authorization, db)
    if not real_user or real_user.is_guest:
        raise HTTPException(status_code=400, detail="Cần đăng nhập tài khoản chính thức để nâng cấp.")
    migrate_guest_data(req.guest_token, real_user, db)
    return {"success": True, "message": "Đã chuyển toàn bộ tài liệu sang tài khoản của bạn thành công!"}

@router.get("/user/library")
def get_user_library(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    if not user or user.is_guest:
        return {"documents": [], "is_guest": True if user else True}

    docs = db.query(Document).filter(Document.user_id == user.id).order_by(Document.created_at.desc()).all()
    return {
        "is_guest": False,
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "subject_name": d.subject_name,
                "summary": d.summary,
                "file_type": d.file_type,
                "is_saved_permanently": d.is_saved_permanently,
                "created_at": d.created_at.strftime("%d/%m/%Y %H:%M"),
                "topic_count": len(d.topics),
                "has_plan": len(d.plans) > 0,
                "latest_plan_id": d.plans[-1].id if d.plans else None
            }
            for d in docs
        ]
    }


# --- Pydantic Schemas ---
class UrlUploadRequest(BaseModel):
    url: str
    gemini_api_key: Optional[str] = None

class PlanGenerateRequest(BaseModel):
    document_id: int
    exam_date: str # YYYY-MM-DD
    daily_hours: float = 2.0
    target_score: float = 8.0
    title: Optional[str] = None
    weekly_schedule: Optional[Dict[str, float]] = None
    gemini_api_key: Optional[str] = None
    active_topic_codes: Optional[List[str]] = None

class ChatRequest(BaseModel):
    document_id: int
    question: str
    gemini_api_key: Optional[str] = None

# --- Document Endpoints ---
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    gemini_api_key: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    try:
        content = await file.read()
        doc_prefix = f"doc_{int(datetime.utcnow().timestamp())}"
        file_type, extracted_text, slide_imgs, total_pages = extract_document_content(file.filename, content, doc_prefix=doc_prefix)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Không thể trích xuất nội dung văn bản từ tệp này.")

        # Save file to disk
        save_path = UPLOAD_DIR / f"{int(datetime.utcnow().timestamp())}_{file.filename}"
        with open(save_path, "wb") as f:
            f.write(content)

        # Analyze syllabus with AI service
        analysis = await ai_service.analyze_syllabus(extracted_text, api_key=gemini_api_key)

        # Create Document record
        is_perm = bool(user and not user.is_guest)
        doc = Document(
            user_id=user.id if user else None,
            is_saved_permanently=is_perm,
            filename=file.filename,
            file_type=file_type,
            file_path=str(save_path),
            extracted_text=extracted_text,
            summary=analysis.get("summary", ""),
            subject_name=analysis.get("subject_name", file.filename),
            total_pages=total_pages,
            document_images=json.dumps(slide_imgs, ensure_ascii=False) if slide_imgs else None
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Create SubjectTopic records
        for idx, t in enumerate(analysis.get("topics", []), 1):
            topic = SubjectTopic(
                document_id=doc.id,
                topic_code=t.get("code", f"CH{idx}"),
                title=t.get("title", f"Chủ đề {idx}"),
                description=t.get("description", ""),
                difficulty=t.get("difficulty", "Trung bình"),
                estimated_hours=float(t.get("estimated_hours", 2.0)),
                importance_score=float(t.get("importance_score", 8.0)),
                order_index=idx
            )
            db.add(topic)
        db.commit()

        return {
            "success": True,
            "document_id": doc.id,
            "subject_name": doc.subject_name,
            "summary": doc.summary,
            "topics": analysis.get("topics", []),
            "files_list": [{"name": doc.filename}]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý file: {str(e)}")

@router.post("/documents/url")
async def upload_url(req: UrlUploadRequest, db: Session = Depends(get_db)):
    try:
        title, extracted_text = await parse_url(req.url)
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Không thể đọc nội dung từ đường link được cung cấp.")

        analysis = await ai_service.analyze_syllabus(extracted_text, api_key=req.gemini_api_key)

        doc = Document(
            filename=title[:80],
            file_type="url",
            file_path=req.url,
            extracted_text=extracted_text,
            summary=analysis.get("summary", ""),
            subject_name=analysis.get("subject_name", title)
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        for idx, t in enumerate(analysis.get("topics", []), 1):
            topic = SubjectTopic(
                document_id=doc.id,
                topic_code=t.get("code", f"CH{idx}"),
                title=t.get("title", f"Chủ đề {idx}"),
                description=t.get("description", ""),
                difficulty=t.get("difficulty", "Trung bình"),
                estimated_hours=float(t.get("estimated_hours", 2.0)),
                importance_score=float(t.get("importance_score", 8.0)),
                order_index=idx
            )
            db.add(topic)
        db.commit()

        return {
            "success": True,
            "document_id": doc.id,
            "subject_name": doc.subject_name,
            "summary": doc.summary,
            "topics": analysis.get("topics", []),
            "files_list": [{"name": doc.filename}]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi cào dữ liệu từ link: {str(e)}")

@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "subject_name": d.subject_name,
            "file_type": d.file_type,
            "created_at": d.created_at.isoformat(),
            "topic_count": len(d.topics)
        }
        for d in docs
    ]

# --- Study Plan Endpoints ---
@router.post("/plans/generate")
async def generate_plan(req: PlanGenerateRequest, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = get_current_user(authorization, db)
    doc = db.query(Document).filter(Document.id == req.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu môn học.")

    try:
        exam_d = datetime.strptime(req.exam_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày thi không hợp lệ (định dạng YYYY-MM-DD).")

    today = date.today()
    if exam_d <= today:
        raise HTTPException(status_code=400, detail="Ngày thi phải lớn hơn ngày hôm nay.")

    # Get topics
    topics = [
        {
            "code": t.topic_code,
            "title": t.title,
            "description": t.description,
            "difficulty": t.difficulty,
            "estimated_hours": t.estimated_hours,
            "importance_score": t.importance_score
        }
        for t in doc.topics
    ]

    if not topics:
        # Fallback if no topics in DB
        analysis = await ai_service.analyze_syllabus(doc.extracted_text, api_key=req.gemini_api_key)
        topics = analysis.get("topics", [])

    if req.active_topic_codes:
        topics = [t for t in topics if t["code"] in req.active_topic_codes]
        if not topics:
            raise HTTPException(status_code=400, detail="Không có chủ đề nào để lên lịch ôn tập.")

    raw_tasks = scheduler.generate_plan(
        topics=topics,
        start_date=today,
        exam_date=exam_d,
        daily_hours=req.daily_hours,
        target_score=req.target_score,
        weekly_schedule=req.weekly_schedule
    )

    plan = StudyPlan(
        user_id=user.id if user else None,
        document_id=doc.id,
        title=req.title or f"Lộ trình ôn thi môn {doc.subject_name}",
        subject_name=doc.subject_name or "Môn học",
        target_score=req.target_score,
        exam_date=exam_d,
        daily_hours=req.daily_hours,
        total_days=(exam_d - today).days
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    for idx, t in enumerate(raw_tasks):
        # Auto-attach matching slides by chapter or task
        task_images = t.get("image_urls")
        if not task_images:
            task_images = find_available_slides(t["title"], t.get("topic_title", ""), None)

        task = StudyTask(
            plan_id=plan.id,
            study_date=t["study_date"],
            day_number=t["day_number"],
            title=t["title"],
            description=t.get("description", ""),
            task_type=t.get("task_type", "study_new"),
            topic_title=t.get("topic_title", ""),
            difficulty=t.get("difficulty", "Trung bình"),
            estimated_minutes=t.get("estimated_minutes", 60),
            is_completed=False,
            order_index=t.get("order_index", 1),
            image_urls=json.dumps(task_images, ensure_ascii=False) if task_images else None
        )
        db.add(task)
    db.commit()

    # Automatically partition & assign slide scopes per task content range
    assign_plan_task_scopes(plan.id, db)

    return get_plan_details_internal(plan.id, db)

def get_plan_details_internal(plan_id: int, db: Session):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch ôn thi.")

    tasks = db.query(StudyTask).filter(StudyTask.plan_id == plan.id).order_by(StudyTask.study_date, StudyTask.order_index).all()
    
    # Retroactively compute scopes if not yet set for existing plans
    if tasks and any(t.slide_scope is None and t.task_type == "study_new" for t in tasks):
        assign_plan_task_scopes(plan.id, db)
        tasks = db.query(StudyTask).filter(StudyTask.plan_id == plan.id).order_by(StudyTask.study_date, StudyTask.order_index).all()

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.is_completed)
    progress_pct = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    today = date.today()
    days_left = max(0, (plan.exam_date - today).days)

    task_dicts = []
    for t in tasks:
        slides = parse_image_urls(t.image_urls)
        task_dicts.append({
            "id": t.id,
            "study_date": t.study_date.isoformat(),
            "day_number": t.day_number,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type,
            "topic_title": t.topic_title,
            "difficulty": t.difficulty,
            "estimated_minutes": t.estimated_minutes,
            "is_completed": t.is_completed,
            "order_index": t.order_index,
            "start_page": t.start_page,
            "end_page": t.end_page,
            "slide_scope": t.slide_scope,
            "image_urls": slides
        })

    return {
        "id": plan.id,
        "document_id": plan.document_id,
        "title": plan.title,
        "subject_name": plan.subject_name,
        "target_score": plan.target_score,
        "exam_date": plan.exam_date.isoformat(),
        "daily_hours": plan.daily_hours,
        "days_left": days_left,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress_percent": progress_pct,
        "tasks": task_dicts
    }

@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    return get_plan_details_internal(plan_id, db)

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(StudyPlan).order_by(StudyPlan.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "subject_name": p.subject_name,
            "target_score": p.target_score,
            "exam_date": p.exam_date.isoformat(),
            "task_count": len(p.tasks)
        }
        for p in plans
    ]

class StudyLessonRequest(BaseModel):
    target_goal: Optional[str] = "advanced" # "basic" | "advanced"
    summary_mode: Optional[str] = "quick" # "quick" (3 phút ngắn gọn) | "detailed" (Đầy đủ chuyên sâu)
    force_refresh: Optional[bool] = False
    gemini_api_key: Optional[str] = None

@router.patch("/tasks/{task_id}/toggle")
def toggle_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ.")

    task.is_completed = not task.is_completed
    task.completed_at = datetime.utcnow() if task.is_completed else None
    db.commit()

    return {"success": True, "task_id": task.id, "is_completed": task.is_completed}

class TaskQuestionRequest(BaseModel):
    question: str
    gemini_api_key: Optional[str] = None

@router.post("/tasks/{task_id}/study-lesson")
async def get_study_lesson(
    task_id: int,
    req: StudyLessonRequest = StudyLessonRequest(),
    db: Session = Depends(get_db)
):
    """Retrieve micro-learning lesson with 3-5 core concepts, 2-min quiz, and advanced materials using RAG.
    Supports Quick (3-min) vs Detailed summary modes.
    Cached permanently in the database so repeated clicks do NOT waste Gemini quota."""
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ học tập.")

    plan = db.query(StudyPlan).filter(StudyPlan.id == task.plan_id).first()
    doc = db.query(Document).filter(Document.id == plan.document_id).first() if plan else None

    is_advanced = (req.target_goal or "advanced") in ["advanced", "g gioi", "gioi", "xuat sac"]
    summary_mode = req.summary_mode if req.summary_mode in ["quick", "detailed"] else "quick"

    # Distinguish cache by goal and summary_mode (e.g. advanced vs basic)
    cached_field = "lesson_data_advanced" if is_advanced else "lesson_data_basic"
    cached_val = getattr(task, cached_field, None)

    if cached_val and not req.force_refresh:
        try:
            cached_json = json.loads(cached_val)
            # If summary_mode matches or cached_json has core_concepts
            if cached_json and "core_concepts" in cached_json and "quick_quiz" in cached_json:
                cached_mode = cached_json.get("summary_mode", "quick")
                if cached_mode == summary_mode:
                    slides = parse_image_urls(task.image_urls)
                    return {
                        "success": True,
                        "task": {
                            "id": task.id,
                            "title": task.title,
                            "topic_title": task.topic_title,
                            "description": task.description,
                            "task_type": task.task_type,
                            "difficulty": task.difficulty,
                            "estimated_minutes": task.estimated_minutes,
                            "is_completed": task.is_completed,
                            "study_date": task.study_date.isoformat(),
                            "day_number": task.day_number,
                            "start_page": task.start_page,
                            "end_page": task.end_page,
                            "slide_scope": task.slide_scope,
                            "image_urls": slides
                        },
                        "target_goal": req.target_goal or "advanced",
                        "summary_mode": summary_mode,
                        "lesson": cached_json,
                        "from_cache": True
                    }
        except Exception:
            pass

    # Retrieve relevant semantic chunks using RAG from the syllabus/document
    relevant_chunks = []
    if doc and doc.extracted_text:
        chunks = chunk_text(doc.extracted_text, chunk_size=700, overlap=100)
        search_query = f"{task.title} {task.topic_title or ''} {task.description or ''}".strip()
        relevant_chunks = search_relevant_chunks(search_query, chunks, top_k=4)

    lesson_data = await ai_service.generate_study_lesson(
        task_title=task.title,
        topic_title=task.topic_title or "",
        context_chunks=relevant_chunks,
        target_goal=req.target_goal or "advanced",
        summary_mode=summary_mode,
        api_key=req.gemini_api_key
    )

    slides = parse_image_urls(task.image_urls)

    # Save to database cache
    try:
        setattr(task, cached_field, json.dumps(lesson_data, ensure_ascii=False))
        db.commit()
    except Exception as e:
        db.rollback()

    return {
        "success": True,
        "task": {
            "id": task.id,
            "title": task.title,
            "topic_title": task.topic_title,
            "description": task.description,
            "task_type": task.task_type,
            "difficulty": task.difficulty,
            "estimated_minutes": task.estimated_minutes,
            "is_completed": task.is_completed,
            "study_date": task.study_date.isoformat(),
            "day_number": task.day_number,
            "start_page": task.start_page,
            "end_page": task.end_page,
            "slide_scope": task.slide_scope,
            "image_urls": slides
        },
        "target_goal": req.target_goal or "advanced",
        "summary_mode": summary_mode,
        "lesson": lesson_data,
        "from_cache": False
    }

class TaskImagesRequest(BaseModel):
    image_urls: List[str]

@router.post("/tasks/{task_id}/images")
def update_task_images(task_id: int, req: TaskImagesRequest, db: Session = Depends(get_db)):
    """Update slide/image URLs attached to a task."""
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ.")
    task.image_urls = json.dumps(req.image_urls, ensure_ascii=False)
    db.commit()
    return {"success": True, "task_id": task.id, "image_urls": req.image_urls}

@router.post("/tasks/{task_id}/upload-images")
async def upload_task_images(
    task_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Directly upload slide/diagram image files for a lesson task and serve statically."""
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ.")

    slides_dir = UPLOAD_DIR / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    current_images = parse_image_urls(task.image_urls)
    for f in files:
        safe_name = f"task_{task_id}_{int(datetime.utcnow().timestamp())}_{secrets.token_hex(3)}_{Path(f.filename).name}"
        dest = slides_dir / safe_name
        content = await f.read()
        with open(dest, "wb") as buffer:
            buffer.write(content)
        current_images.append(f"/uploads/slides/{safe_name}")

    task.image_urls = json.dumps(current_images, ensure_ascii=False)
    db.commit()
    return {"success": True, "task_id": task.id, "image_urls": current_images}

@router.post("/tasks/{task_id}/ask")
async def ask_task_question(
    task_id: int,
    req: TaskQuestionRequest,
    db: Session = Depends(get_db)
):
    """Direct Q&A inside Study Modal answering student queries specifically about this task and syllabus."""
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ học tập.")

    plan = db.query(StudyPlan).filter(StudyPlan.id == task.plan_id).first()
    doc = db.query(Document).filter(Document.id == plan.document_id).first() if plan else None

    context_chunks = []
    if doc and doc.extracted_text:
        chunks = chunk_text(doc.extracted_text, chunk_size=700, overlap=100)
        search_query = f"{task.title} {task.topic_title or ''} {req.question}".strip()
        context_chunks = search_relevant_chunks(search_query, chunks, top_k=4)

    answer = await ai_service.answer_question(
        question=req.question,
        context_chunks=context_chunks,
        api_key=req.gemini_api_key
    )

    return {
        "success": True,
        "question": req.question,
        "answer": answer
    }

@router.post("/plans/{plan_id}/reschedule")
def reschedule_plan(plan_id: int, db: Session = Depends(get_db)):
    """Re-distribute incomplete tasks into remaining days."""
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch.")

    today = date.today()
    tasks = db.query(StudyTask).filter(StudyTask.plan_id == plan.id).all()

    existing_task_dicts = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type,
            "topic_title": t.topic_title,
            "difficulty": t.difficulty,
            "estimated_minutes": t.estimated_minutes,
            "is_completed": t.is_completed,
            "study_date": t.study_date,
            "day_number": t.day_number,
            "order_index": t.order_index
        }
        for t in tasks
    ]

    redistributed = scheduler.reschedule_missed_tasks(
        existing_tasks=existing_task_dicts,
        today=today,
        exam_date=plan.exam_date,
        daily_hours=plan.daily_hours
    )

    # Delete existing uncompleted tasks and insert re-calculated tasks
    db.query(StudyTask).filter(StudyTask.plan_id == plan.id, StudyTask.is_completed == False).delete()
    db.commit()

    for item in redistributed:
        if not item.get("is_completed"):
            new_task = StudyTask(
                plan_id=plan.id,
                study_date=item["study_date"],
                day_number=item["day_number"],
                title=item["title"],
                description=item.get("description", ""),
                task_type=item.get("task_type", "study_new"),
                topic_title=item.get("topic_title", ""),
                difficulty=item.get("difficulty", "Trung bình"),
                estimated_minutes=item.get("estimated_minutes", 60),
                is_completed=False,
                order_index=item.get("order_index", 1)
            )
            db.add(new_task)
    db.commit()

    return get_plan_details_internal(plan.id, db)

# --- AI Chatbot RAG Endpoints ---
@router.post("/chat/ask")
async def ask_chat(req: ChatRequest, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == req.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu môn học.")

    # Save user message
    user_msg = ChatMessage(document_id=doc.id, role="user", content=req.question)
    db.add(user_msg)
    db.commit()

    # RAG search
    chunks = chunk_text(doc.extracted_text)
    relevant_chunks = search_relevant_chunks(req.question, chunks, top_k=3)

    # AI answer
    answer = await ai_service.answer_question(
        question=req.question,
        context_chunks=relevant_chunks,
        api_key=req.gemini_api_key
    )

    # Save assistant message
    ai_msg = ChatMessage(document_id=doc.id, role="assistant", content=answer)
    db.add(ai_msg)
    db.commit()

    return {
        "question": req.question,
        "answer": answer,
        "sources_count": len(relevant_chunks)
    }

@router.get("/chat/{doc_id}/history")
def get_chat_history(doc_id: int, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.document_id == doc_id).order_by(ChatMessage.created_at.asc()).all()
    return [
        {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in messages
    ]

# --- Google Calendar iCal (.ics) Export ---
@router.get("/plans/{plan_id}/export-ical")
def export_ical(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch.")

    tasks = db.query(StudyTask).filter(StudyTask.plan_id == plan.id).order_by(StudyTask.study_date).all()
    
    cal_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ExamPlan AI//Lộ Trình Ôn Thi Đại Học//VI",
        f"X-WR-CALNAME:Lộ trình ôn thi {plan.subject_name}"
    ]

    for t in tasks:
        dt_str = t.study_date.strftime("%Y%m%d")
        cal_lines.extend([
            "BEGIN:VEVENT",
            f"UID:examplan-{t.id}@{plan.id}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{dt_str}",
            f"DTEND;VALUE=DATE:{dt_str}",
            f"SUMMARY:[{plan.subject_name}] {t.title}",
            f"DESCRIPTION:{t.description or 'Ôn thi cùng ExamPlan AI'}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])

    cal_lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(cal_lines)

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="exam_plan_{plan.id}.ics"'}
    )

# --- Sample Syllabus One-Click Demo ---
SAMPLE_SYLLABUS = """
TRƯỜNG ĐẠI HỌC KINH TẾ QUỐC DÂN
KHOA LÝ LUẬN CHÍNH TRỊ
ĐỀ CƯƠNG ÔN THI HỌC PHẦN: TRIẾT HỌC MÁC - LÊNIN (3 TÍN CHỈ)

CHƯƠNG 1: TRIẾT HỌC VÀ VAI TRÒ CỦA TRIẾT HỌC TRONG ĐỜI SỐNG XÃ HỘI
- Vấn đề cơ bản của triết học: Mối quan hệ giữa tư duy và tồn tại, hai mặt vấn đề cơ bản.
- Chủ nghĩa duy vật và chủ nghĩa duy tâm trong lịch sử.
- Sự ra đời và phát triển của Triết học Mác - Lênin, các giai đoạn và tiền đề lý luận khoa học.
- Đối tượng và chức năng thế giới quan, phương pháp luận của triết học Mác - Lênin.

CHƯƠNG 2: CHỦ NGHĨA DUY VẬT BIỆN CHỨNG
- Vật chất và phương thức tồn tại của vật chất (Định nghĩa vật chất của Lênin, vận động, không gian, thời gian).
- Nguồn gốc, bản chất và kết cấu của ý thức. Mối quan hệ biện chứng giữa vật chất và ý thức.
- Hai nguyên lý cơ bản của phép biện chứng duy vật: Nguyên lý về mối liên hệ phổ biến và Nguyên lý về sự phát triển.
- Sáu cặp phạm trù cơ bản: Cái riêng - Cái chung; Nguyên nhân - Kết quả; Tất nhiên - Ngẫu nhiên; Nội dung - Hình thức; Bản chất - Hiện tượng; Khả năng - Hiện thực.
- Ba quy luật cơ bản: Quy luật lượng - chất; Quy luật mâu thuẫn (hạt nhân phép biện chứng); Quy luật phủ định của phủ định.
- Lý luận nhận thức duy vật biện chứng: Thực tiễn và vai trò của thực tiễn đối với nhận thức; Con đường biện chứng của sự nhận thức chân lý.

CHƯƠNG 3: CHỦ NGHĨA DUY VẬT LỊCH SỬ
- Học thuyết hình thái kinh tế - xã hội: Sản xuất vật chất là cơ sở của sự tồn tại và phát triển xã hội; Quy luật quan hệ sản xuất phù hợp với trình độ phát triển của lực lượng sản xuất.
- Biện chứng giữa cơ sở hạ tầng và kiến trúc thượng tầng.
- Giai cấp và đấu tranh giai cấp, nhà nước và cách mạng xã hội.
- Ý thức xã hội và các hình thái ý thức xã hội.
- Triết học về con người: Bản chất con người là tổng hòa các quan hệ xã hội; Vai trò của quần chúng nhân dân và lãnh tụ trong lịch sử.

CẤU TRÚC ĐỀ THI TỰ LUẬN (90 PHÚT):
- Câu 1 (3 điểm): Lý thuyết cơ bản (Nguyên lý, quy luật hoặc phạm trù).
- Câu 2 (4 điểm): Phân tích sâu nội dung triết học và làm rõ cơ chế biện chứng.
- Câu 3 (3 điểm): Vận dụng thực tiễn vào học tập, rèn luyện bản thân và phát triển kinh tế - xã hội tại Việt Nam hiện nay.
"""

@router.post("/demo/load-sample")
async def load_sample_syllabus(db: Session = Depends(get_db)):
    """Pre-loads the authentic sample university syllabus for 1-click test."""
    analysis = await ai_service.analyze_syllabus(SAMPLE_SYLLABUS)
    doc = Document(
        filename="De_cuong_on_thi_Triet_hoc_Mac_Lenin.txt",
        file_type="txt",
        file_path="sample/triet_hoc.txt",
        extracted_text=SAMPLE_SYLLABUS,
        summary=analysis.get("summary", "Đề cương ôn thi môn Triết học Mác - Lênin 3 tín chỉ với 3 chương trọng tâm và hướng dẫn cấu trúc đề thi 90 phút."),
        subject_name="Triết học Mác - Lênin"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    for idx, t in enumerate(analysis.get("topics", []), 1):
        topic = SubjectTopic(
            document_id=doc.id,
            topic_code=t.get("code", f"CH{idx}"),
            title=t.get("title", f"Chủ đề {idx}"),
            description=t.get("description", ""),
            difficulty=t.get("difficulty", "Trung bình"),
            estimated_hours=float(t.get("estimated_hours", 2.0)),
            importance_score=float(t.get("importance_score", 8.5)),
            order_index=idx
        )
        db.add(topic)
    db.commit()

    return {
        "success": True,
        "document_id": doc.id,
        "subject_name": doc.subject_name,
        "summary": doc.summary,
        "topics": analysis.get("topics", []),
        "files_list": [
            {"name": "1. Chuong_1_Triet_Hoc_Va_Vai_Tro.pdf", "topic_code": "CH1"},
            {"name": "2. Chuong_2_Duy_Vat_Bien_Chung.pdf", "topic_code": "CH2"},
            {"name": "3. Chuong_3_Duy_Vat_Lich_Su.pdf", "topic_code": "CH3"}
        ]
    }

# --- Timetable / Schedule Upload Endpoint ---
@router.post("/timetable/upload")
async def upload_timetable(
    file: UploadFile = File(...),
    gemini_api_key: Optional[str] = Form(None)
):
    try:
        content = await file.read()
        result = timetable_service.parse_file(file.filename, content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc thời khóa biểu/lịch: {str(e)}")

# --- Multi-File Upload & Document Deletion ---
@router.post("/documents/upload-multiple")
async def upload_multiple_documents(
    files: List[UploadFile] = File(...),
    gemini_api_key: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    if not files:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 tệp.")

    combined_texts = []
    file_summaries = []

    for f in files:
        content = await f.read()
        file_type, extracted = extract_document_content(f.filename, content)
        if extracted.strip():
            save_path = UPLOAD_DIR / f"{int(datetime.utcnow().timestamp())}_{f.filename}"
            with open(save_path, "wb") as out:
                out.write(content)
            combined_texts.append(f"=== TỆP: {f.filename} ===\n{extracted.strip()}")
            file_summaries.append(f.filename)

    if not combined_texts:
        raise HTTPException(status_code=400, detail="Không thể trích xuất văn bản từ các tệp này.")

    full_text = "\n\n".join(combined_texts)
    analysis = await ai_service.analyze_syllabus(full_text, api_key=gemini_api_key)

    doc_name = file_summaries[0] if len(file_summaries) == 1 else f"Bộ {len(file_summaries)} tài liệu: {', '.join(file_summaries[:2])}..."
    is_perm = bool(user and not user.is_guest)
    doc = Document(
        user_id=user.id if user else None,
        is_saved_permanently=is_perm,
        filename=doc_name,
        file_type="multi",
        file_path=str(UPLOAD_DIR),
        extracted_text=full_text,
        summary=analysis.get("summary", ""),
        subject_name=analysis.get("subject_name", doc_name)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    for idx, t in enumerate(analysis.get("topics", []), 1):
        topic = SubjectTopic(
            document_id=doc.id,
            topic_code=t.get("code", f"CH{idx}"),
            title=t.get("title", f"Chủ đề {idx}"),
            description=t.get("description", ""),
            difficulty=t.get("difficulty", "Trung bình"),
            estimated_hours=float(t.get("estimated_hours", 2.0)),
            importance_score=float(t.get("importance_score", 8.0)),
            order_index=idx
        )
        db.add(topic)
    db.commit()

    return {
        "success": True,
        "document_id": doc.id,
        "subject_name": doc.subject_name,
        "summary": doc.summary,
        "topics": analysis.get("topics", []),
        "files_count": len(file_summaries),
        "files_list": [{"name": fn, "topic_code": f"CH{idx}"} for idx, fn in enumerate(file_summaries, 1)]
    }

@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu cần xóa.")

    if doc.file_path and Path(doc.file_path).exists() and Path(doc.file_path).is_file():
        try:
            Path(doc.file_path).unlink()
        except Exception:
            pass

    db.delete(doc)
    db.commit()
    return {"success": True, "deleted_id": document_id}

@router.delete("/documents/{document_id}/topics/{topic_code}")
def delete_document_topic(document_id: int, topic_code: str, db: Session = Depends(get_db)):
    topic = db.query(SubjectTopic).filter(
        SubjectTopic.document_id == document_id,
        SubjectTopic.topic_code == topic_code
    ).first()
    if not topic:
        try:
            idx = int(topic_code)
            topic = db.query(SubjectTopic).filter(
                SubjectTopic.document_id == document_id,
                SubjectTopic.order_index == idx
            ).first()
        except ValueError:
            pass

    if topic:
        db.delete(topic)
        db.commit()
        remaining = db.query(SubjectTopic).filter(SubjectTopic.document_id == document_id).count()
        return {"success": True, "deleted_code": topic_code, "remaining_count": remaining}
    return {"success": False, "message": "Không tìm thấy chủ đề."}
