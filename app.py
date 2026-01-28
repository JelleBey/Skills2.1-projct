# app.py - SECURITY HARDENED + FLEXIBLE IP CONFIGURATION
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Cookie, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, timedelta
from typing import Optional
import io
import os
import re
import logging

import torch
import torch.nn as nn
from torchvision import models, transforms

import asyncpg
import bcrypt
import jwt
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/leaf-health/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------- CORS - FLEXIBLE IP CONFIGURATION ----------
# Get allowed origins from environment variable (comma-separated)
# Just update .env file when your IP changes!
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]

# If no origins specified, allow localhost for development
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
    logger.warning("No ALLOWED_ORIGINS set in .env, using localhost only")

logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

BASE_DIR = Path(__file__).resolve().parent

# Serve static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

# ---------- Database Configuration ----------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in environment variables")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be set in environment variables for security")
    
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Database connection pool
db_pool = None

security = HTTPBearer()

# ---------- Password Validation ----------
def validate_password_strength(password: str) -> None:
    """Validate password meets security requirements"""
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character")

# ---------- Pydantic Models ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    
    @validator('password')
    def validate_password(cls, v):
        validate_password_strength(v)
        return v
    
    @validator('first_name', 'last_name')
    def validate_name(cls, v):
        if len(v) < 1 or len(v) > 50:
            raise ValueError("Name must be between 1 and 50 characters")
        if not re.match(r"^[a-zA-Z\s\-]+$", v):
            raise ValueError("Name can only contain letters, spaces, and hyphens")
        return v.strip()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

# ---------- Database Functions ----------
async def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL, 
            min_size=1, 
            max_size=10,
            command_timeout=60
        )
    return db_pool

async def close_db_pool():
    global db_pool
    if db_pool:
        await db_pool.close()

# ---------- Authentication Helpers ----------
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token"""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"Expired token attempt")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_from_cookie(access_token: Optional[str] = Cookie(None)):
    """Dependency to get the current authenticated user from HttpOnly cookie"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(access_token)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, first_name, last_name FROM users WHERE id = $1",
            payload["user_id"]
        )
    
    if not user:
        logger.warning(f"Token valid but user not found: {payload['user_id']}")
        raise HTTPException(status_code=401, detail="User not found")
    
    return dict(user)

# ---------- File Validation ----------
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_image_file(file_bytes: bytes) -> Image.Image:
    """Validate uploaded file is actually an image and safe"""
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        img = Image.open(io.BytesIO(file_bytes))
        
        if img.format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_IMAGE_FORMATS)}"
            )
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")

# ---------- Startup/Shutdown Events ----------
@app.on_event("startup")
async def startup():
    logger.info("Application starting up...")
    await get_db_pool()
    logger.info("Database pool initialized")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down...")
    await close_db_pool()
    logger.info("Database pool closed")

# ---------- Routes ----------
@app.get("/")
async def index(access_token: Optional[str] = Cookie(None)):
    """Serve index.html only to authenticated users, redirect otherwise"""
    if not access_token:
        return RedirectResponse(url="/login.html", status_code=303)
    
    try:
        decode_token(access_token)
    except HTTPException:
        return RedirectResponse(url="/login.html", status_code=303)
    
    return HTMLResponse((BASE_DIR / "index.html").read_text(encoding="utf-8"))

@app.get("/login.html", response_class=HTMLResponse)
def login_page():
    return (BASE_DIR / "login.html").read_text(encoding="utf-8")

@app.get("/register.html", response_class=HTMLResponse)
def register_page():
    return (BASE_DIR / "register.html").read_text(encoding="utf-8")

@app.post("/api/register", response_model=TokenResponse)
@limiter.limit("3/hour")
async def register(request: Request, user_data: UserRegister, response: Response):
    """Register a new user and set HttpOnly cookie"""
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user_data.email)
            if existing:
                logger.warning(f"Registration attempt with existing email: {user_data.email}")
                raise HTTPException(status_code=400, detail="Email already registered")
            
            hashed_pw = hash_password(user_data.password)
            
            user = await conn.fetchrow(
                """INSERT INTO users (email, password_hash, first_name, last_name) 
                   VALUES ($1, $2, $3, $4) 
                   RETURNING id, email, first_name, last_name""",
                user_data.email, hashed_pw, user_data.first_name, user_data.last_name
            )
        
        logger.info(f"New user registered: {user['email']}")
        
        token = create_access_token(user["id"], user["email"])
        
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="strict",
            secure=False,  # Change to True when using HTTPS
            max_age=JWT_EXPIRATION_HOURS * 3600
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin, response: Response):
    """Login a user and set HttpOnly cookie"""
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, email, password_hash, first_name, last_name FROM users WHERE email = $1",
                credentials.email
            )
        
        if not user or not verify_password(credentials.password, user["password_hash"]):
            logger.warning(f"Failed login attempt for: {credentials.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        logger.info(f"Successful login: {user['email']}")
        
        token = create_access_token(user["id"], user["email"])
        
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="strict",
            secure=False,  # Change to True when using HTTPS
            max_age=JWT_EXPIRATION_HOURS * 3600
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user_from_cookie)):
    """Get current user information"""
    return current_user

@app.post("/api/logout")
async def logout(response: Response):
    """Logout user and clear HttpOnly cookie"""
    response.delete_cookie("access_token", samesite="strict")
    logger.info("User logged out")
    return {"message": "Logged out successfully"}

# ---------- AI Model ----------
CLASS_NAMES = ["Early_blight", "Late_blight", "Tomato_Yellow_Leaf_Curl_Virus", "healthy"]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = models.efficientnet_b0(weights=None)
model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(CLASS_NAMES))

MODEL_PATH = BASE_DIR / "tomato_model.pt"
if not MODEL_PATH.exists():
    raise RuntimeError(f"Model file not found: {MODEL_PATH}")

state = torch.load(str(MODEL_PATH), map_location=device)
model.load_state_dict(state)
model.to(device)
model.eval()

preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

@app.get("/health")
def health():
    return {"status": "ok", "device": str(device)}

@app.post("/predict")
@limiter.limit("10/minute")
async def predict(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_from_cookie)
):
    """Predict leaf health (requires authentication)"""
    logger.info(f"Prediction request from user: {current_user['email']}")
    
    img_bytes = await file.read()
    img = validate_image_file(img_bytes)
    
    try:
        x = preprocess(img).unsqueeze(0).to(device)
        
        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=1)[0]
            idx = int(torch.argmax(probs).item())
        
        predicted_class = CLASS_NAMES[idx]
        confidence = float(probs[idx].item())
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO analyses (user_id, predicted_class, confidence, analyzed_at)
                   VALUES ($1, $2, $3, $4)""",
                current_user["id"], predicted_class, confidence, datetime.utcnow()
            )
        
        logger.info(f"Prediction complete: {predicted_class} ({confidence:.2f})")
        
        return {
            "class": predicted_class,
            "confidence": confidence
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")
