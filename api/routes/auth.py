from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from auth.auth_handler import verify_password, create_access_token
from auth.dependencies import get_current_user
from models.users import User
from db.session import get_db

from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/token", response_model=Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=dict)
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "name": current_user.full_name
    }
