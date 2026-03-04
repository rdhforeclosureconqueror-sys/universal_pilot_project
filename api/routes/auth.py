from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from app.models.users import User
from app.services.auth_service import AuthService
from db.session import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])


class Token(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    email: str
    password: str


class CreateAdminRequest(BaseModel):
    email: str
    password: str
    admin_secret: str | None = None


class AssumeRoleRequest(BaseModel):
    role_name: str
    case_id: str | None = None
    program_key: str | None = None
    duration_minutes: int = 30


@router.post("/register", response_model=dict)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    user = AuthService(db).register_user(email=request.email, password=request.password)
    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value if user.role else None,
    }


@router.post("/create-admin", response_model=dict)
def create_admin(request: CreateAdminRequest, db: Session = Depends(get_db)):
    user = AuthService(db).create_admin(
        email=request.email,
        password=request.password,
        admin_secret=request.admin_secret,
    )
    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value if user.role else None,
    }


@router.post("/token", response_model=Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    return AuthService(db).login(username=username, password=password)


@router.post("/assume-role")
def assume_role(
    request: AssumeRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = PolicyAuthorizer(db).assume_role(
        user=current_user,
        role_name=request.role_name,
        case_id=request.case_id,
        program_key=request.program_key,
        duration_minutes=request.duration_minutes,
    )
    return {
        "role_session_id": str(session.id),
        "role_name": session.role_name,
        "scope_case_id": str(session.scope_case_id) if session.scope_case_id else None,
        "scope_program_key": session.scope_program_key,
        "expires_at": session.expires_at,
    }


@router.get("/me", response_model=dict)
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value if current_user.role else None,
        "name": current_user.full_name,
    }
