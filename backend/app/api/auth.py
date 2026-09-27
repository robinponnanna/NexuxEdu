from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, User, Student, Faculty, Parent
from app.core.security import verify_password, create_access_token, decode_access_token
from app.models.schemas import LoginRequest, TokenResponse, UserResponse, UserSecurityClaims

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_bearer = HTTPBearer(auto_error=False)

async def get_current_user_claims(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)) -> UserSecurityClaims:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token."
        )
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )
    return UserSecurityClaims(**payload)

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == req.email.strip().lower())
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )
            
        department = None
        student_id = None
        ward_id = None
        bus_id = None
        
        # Load role-specific profile bindings
        if user.role == "student":
            s_stmt = select(Student).where(Student.user_id == user.id)
            s_res = await session.execute(s_stmt)
            st = s_res.scalar_one_or_none()
            if st:
                student_id = st.id
                department = st.department
                bus_id = st.bus_id
        elif user.role == "faculty":
            f_stmt = select(Faculty).where(Faculty.user_id == user.id)
            f_res = await session.execute(f_stmt)
            fac = f_res.scalar_one_or_none()
            if fac:
                department = fac.department
        elif user.role == "parent":
            p_stmt = select(Parent).where(Parent.user_id == user.id)
            p_res = await session.execute(p_stmt)
            p = p_res.scalar_one_or_none()
            if p:
                # Find ward
                w_stmt = select(Student).where(Student.parent_id == p.id)
                w_res = await session.execute(w_stmt)
                ward = w_res.scalar_one_or_none()
                if ward:
                    ward_id = ward.id
                    department = ward.department
                    bus_id = ward.bus_id
                    
        claims_dict = {
            "user_id": user.id,
            "public_id": user.public_id,
            "role": user.role,
            "name": user.name,
            "email": user.email,
            "department": department,
            "student_id": student_id,
            "ward_id": ward_id,
            "bus_id": bus_id
        }
        
        token = create_access_token(claims_dict)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                public_id=user.public_id,
                name=user.name,
                email=user.email,
                role=user.role,
                department=department,
                student_id=student_id,
                ward_id=ward_id,
                bus_id=bus_id
            )
        )

@router.get("/me", response_model=UserResponse)
async def get_me(claims: UserSecurityClaims = Depends(get_current_user_claims)):
    return UserResponse(
        id=claims.user_id,
        public_id=claims.public_id,
        name=claims.name,
        email=claims.email,
        role=claims.role,
        department=claims.department,
        student_id=claims.student_id,
        ward_id=claims.ward_id,
        bus_id=claims.bus_id
    )
