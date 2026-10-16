"""Teacher routes — class management + dashboard.

All endpoints require teacher or admin role (via ``require_teacher``).
Teachers can only see/modify their own classes; admin bypasses ownership
checks (acts as global teacher).

Phase 3 introduces the API surface; Phase 4 will build the matching UI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, require_teacher
from integrity_checker.db.models import Class, User
from integrity_checker.db.repository import Repository

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class ClassResponse(BaseModel):
    id: int
    name: str
    description: str | None
    teacher_id: int
    teacher_username: str
    created_at: str
    student_count: int = 0
    essay_count: int = 0


class AddStudentRequest(BaseModel):
    student_id: int


class StudentInClass(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str | None
    is_active: bool


class ClassEssaySummary(BaseModel):
    id: int
    filename: str
    uploaded_at: str
    user_id: int | None
    username: str | None
    num_pages: int


class TeacherDashboardResponse(BaseModel):
    total_classes: int
    total_students: int
    total_essays: int
    pending_reviews: int
    classes: list[ClassResponse]


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _class_to_response(cls: Class, repo: Repository, *, essay_count: int | None = None) -> ClassResponse:
    student_count = repo.count_students_in_class(cls.id)
    # If caller already computed essay_count (to avoid duplicate query), reuse it.
    if essay_count is None:
        essay_count = len(repo.get_class_essays(cls.id))
    teacher = repo.get_user_by_id(cls.teacher_id)
    return ClassResponse(
        id=cls.id,
        name=cls.name,
        description=cls.description,
        teacher_id=cls.teacher_id,
        teacher_username=teacher.username if teacher else "unknown",
        created_at=cls.created_at.isoformat() if cls.created_at else "",
        student_count=student_count,
        essay_count=essay_count,
    )


def _student_to_response(student: User) -> StudentInClass:
    return StudentInClass(
        id=student.id,
        username=student.username,
        email=student.email,
        full_name=student.full_name,
        is_active=bool(student.is_active),
    )


def _ensure_teacher_owns_class(teacher: User, cls: Class) -> None:
    """403 nếu teacher không phụ trách class này. Admin bypass."""
    if teacher.role == "admin":
        return
    if cls.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not your class")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/classes", response_model=list[ClassResponse])
def list_my_classes(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Teacher: list classes mình phụ trách. Admin: list all."""
    repo = Repository(db)
    if teacher.role == "admin":
        classes = repo.list_all_classes()
    else:
        classes = repo.list_classes_for_teacher(teacher.id)
    # Compute essay lists ONCE per class (avoids N+1 — without caching,
    # _class_to_response would re-query get_class_essays for each class,
    # making the endpoint O(N²) in queries).
    return [
        _class_to_response(
            c, repo, essay_count=len(repo.get_class_essays(c.id))
        )
        for c in classes
    ]


@router.post("/classes", response_model=ClassResponse, status_code=201)
def create_class(
    request: ClassCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Teacher tạo class mới (admin cũng OK)."""
    repo = Repository(db)
    if repo.get_class_by_name(request.name):
        raise HTTPException(status_code=400, detail="Class name already exists")
    cls = repo.create_class(
        name=request.name,
        teacher_id=teacher.id,
        description=request.description,
    )
    repo.commit()
    return _class_to_response(cls, repo)


@router.get("/classes/{class_id}/students", response_model=list[StudentInClass])
def list_class_students(
    class_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """List students trong class. Enforce: teacher chỉ xem class mình phụ trách."""
    repo = Repository(db)
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    _ensure_teacher_owns_class(teacher, cls)
    students = repo.list_students_in_class(class_id)
    return [_student_to_response(s) for s in students]


@router.post("/classes/{class_id}/students", response_model=MessageResponse)
def add_student_to_class(
    class_id: int,
    request: AddStudentRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Add student to class. Idempotent."""
    repo = Repository(db)
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    _ensure_teacher_owns_class(teacher, cls)
    student = repo.get_user_by_id(request.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.role != "user":
        raise HTTPException(
            status_code=400,
            detail="Only users with role 'user' can be added as students",
        )
    repo.add_student_to_class(class_id, request.student_id)
    repo.commit()
    return MessageResponse(message=f"Student {student.username} added to class {cls.name}")


@router.delete(
    "/classes/{class_id}/students/{student_id}", response_model=MessageResponse,
)
def remove_student_from_class(
    class_id: int,
    student_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Remove student from class."""
    repo = Repository(db)
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    _ensure_teacher_owns_class(teacher, cls)
    if not repo.remove_student_from_class(class_id, student_id):
        raise HTTPException(status_code=404, detail="Student is not in this class")
    repo.commit()
    return MessageResponse(message="Student removed from class")


@router.get("/classes/{class_id}/essays", response_model=list[ClassEssaySummary])
def list_class_essays(
    class_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """List essays của students trong class."""
    repo = Repository(db)
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    _ensure_teacher_owns_class(teacher, cls)
    essays = repo.get_class_essays(class_id)
    out: list[ClassEssaySummary] = []
    for essay in essays:
        student = repo.get_user_by_id(essay.user_id) if essay.user_id else None
        out.append(
            ClassEssaySummary(
                id=essay.id,
                filename=essay.filename,
                uploaded_at=essay.uploaded_at.isoformat() if essay.uploaded_at else "",
                user_id=essay.user_id,
                username=student.username if student else None,
                num_pages=essay.num_pages,
            )
        )
    return out


@router.get("/dashboard", response_model=TeacherDashboardResponse)
def teacher_dashboard(
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """Aggregated stats cho 1 teacher (admin sees their own subset, no
    global admin dashboard — that's Phase 4)."""
    repo = Repository(db)
    if teacher.role == "admin":
        classes = repo.list_all_classes()
    else:
        classes = repo.list_classes_for_teacher(teacher.id)
    # Compute essay lists ONCE per class to avoid duplicate query in
    # _class_to_response (otherwise total_essays is inflated by 2x or 3x).
    essays_per_class: dict[int, list] = {
        c.id: repo.get_class_essays(c.id) for c in classes
    }
    total_students = sum(repo.count_students_in_class(c.id) for c in classes)
    total_essays = sum(len(essays_per_class[c.id]) for c in classes)
    pending_reviews = (
        repo.count_pending_reviews_for_teacher(teacher.id)
        if teacher.role == "teacher"
        else 0
    )
    return TeacherDashboardResponse(
        total_classes=len(classes),
        total_students=total_students,
        total_essays=total_essays,
        pending_reviews=pending_reviews,
        classes=[
            _class_to_response(c, repo, essay_count=len(essays_per_class[c.id]))
            for c in classes
        ],
    )
