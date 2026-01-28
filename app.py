# app.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import io
import os

import torch
import torch.nn as nn
from torchvision import models, transforms

import asyncpg
import bcrypt
import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://44.195.35.212", "http://44.195.35.212:8000", "*"],  # AWS EC2 Instance
    allow_credentials=True,  # Required for HttpOnly cookie auth
    allow_methods=["*"],
    allow_headers=["*"],
    # NOTE: Production should tighten origins to actual deployed domain(s)
)

BASE_DIR = Path(__file__).resolve().parent

# Serve static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

# ---------- Database Configuration ----------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in environment variables")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-change-this")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Database connection pool
db_pool = None

security = HTTPBearer()

# ---------- Pydantic Models ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

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
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return db_pool

async def close_db_pool():
    global db_pool
    if db_pool:
        await db_pool.close()

# ---------- Authentication Helpers ----------
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token"""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get the current authenticated user (HTTPBearer)"""
    token = credentials.credentials
    payload = decode_token(token)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, first_name, last_name FROM users WHERE id = $1",
            payload["user_id"]
        )
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return dict(user)


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
        raise HTTPException(status_code=401, detail="User not found")
    
    return dict(user)


async def get_current_user_dual(
    access_token: Optional[str] = Cookie(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    """Dependency supporting BOTH cookie and Bearer token authentication"""
    token = None
    
    # Try cookie first
    if access_token:
        token = access_token
    # Fall back to Authorization header
    elif credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, first_name, last_name FROM users WHERE id = $1",
            payload["user_id"]
        )
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return dict(user)

# ---------- Startup/Shutdown Events ----------
@app.on_event("startup")
async def startup():
    await get_db_pool()

@app.on_event("shutdown")
async def shutdown():
    await close_db_pool()

# ---------- Routes ----------
@app.get("/")
async def index(access_token: Optional[str] = Cookie(None)):
    """Serve index.html only to authenticated users, redirect otherwise"""
    # If no cookie, redirect to login
    if not access_token:
        return RedirectResponse(url="/login.html", status_code=303)
    
    # Verify the token is valid
    try:
        decode_token(access_token)
    except HTTPException:
        # Invalid/expired token - redirect to login
        return RedirectResponse(url="/login.html", status_code=303)
    
    # User is authenticated - serve the page
    return HTMLResponse((BASE_DIR / "index.html").read_text(encoding="utf-8"))

@app.get("/login.html", response_class=HTMLResponse)
def login_page():
    return (BASE_DIR / "login.html").read_text(encoding="utf-8")

@app.get("/register.html", response_class=HTMLResponse)
def register_page():
    return (BASE_DIR / "register.html").read_text(encoding="utf-8")

@app.post("/api/register", response_model=TokenResponse)
async def register(user_data: UserRegister, response: Response):
    """Register a new user and set HttpOnly cookie"""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Check if user already exists
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user_data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        hashed_pw = hash_password(user_data.password)
        
        # Insert user
        user = await conn.fetchrow(
            """INSERT INTO users (email, password_hash, first_name, last_name) 
               VALUES ($1, $2, $3, $4) 
               RETURNING id, email, first_name, last_name""",
            user_data.email, hashed_pw, user_data.first_name, user_data.last_name
        )
    
    # Create token
    token = create_access_token(user["id"], user["email"])
    
    # Set HttpOnly cookie
    # For localhost: secure=False, samesite="lax"
    # For production: secure=True (HTTPS only), samesite="strict" or "lax"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Change to True in production (HTTPS only)
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

@app.post("/api/login", response_model=TokenResponse)
async def login(credentials: UserLogin, response: Response):
    """Login a user and set HttpOnly cookie"""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash, first_name, last_name FROM users WHERE email = $1",
            credentials.email
        )
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create token
    token = create_access_token(user["id"], user["email"])
    
    # Set HttpOnly cookie
    # For localhost: secure=False, samesite="lax"
    # For production: secure=True (HTTPS only), samesite="strict" or "lax"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Change to True in production (HTTPS only)
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

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@app.post("/api/logout")
async def logout(response: Response):
    """Logout user and clear HttpOnly cookie"""
    response.delete_cookie("access_token", samesite="lax")
    return {"message": "Logged out successfully"}

# ---------- AI Model (UNCHANGED) ----------
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
async def predict(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user_dual)
):
    """Predict leaf health (requires authentication)"""
    print(f"Received file: {file.filename}, content_type: {file.content_type}")
    print(f"User: {current_user['email']}")
    
    img_bytes = await file.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")
    
    x = preprocess(img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(torch.argmax(probs).item())
    
    predicted_class = CLASS_NAMES[idx]
    confidence = float(probs[idx].item())
    
    # Save analysis to database
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO analyses (user_id, predicted_class, confidence, analyzed_at)
               VALUES ($1, $2, $3, $4)""",
            current_user["id"], predicted_class, confidence, datetime.utcnow()
        )
    
    return {
        "class": predicted_class,
        "confidence": confidence
    }