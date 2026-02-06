from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from auth.auth_handler import verify_password, create_access_token
from auth.authorization import PolicyAuthorizer
from auth.dependencies import get_current_user
from models.users import User
from db.session import get_db

from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])


class Token(BaseModel):
    access_token: str
    token_type: str


class AssumeRoleRequest(BaseModel):
    role_name: str
    case_id: str | None = None
    program_key: str | None = None
    duration_minutes: int = 30


@router.post("/token", response_model=Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


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
        "name": current_user.full_name
    }
