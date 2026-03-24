"""High School Management System API.

This app provides activities discovery and role-based sign-up flows
for students and teachers at Mergington High School.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-this-in-production"),
    max_age=60 * 60 * 24,
    same_site="lax",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir,
          "static")), name="static")

USERS_FILE = current_dir / "users.json"


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = Field(default="student")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users() -> dict:
    with open(USERS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_users(users: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=2)


def ensure_users_file() -> None:
    if USERS_FILE.exists():
        return

    seed_users = {
        "admin@mergington.edu": {
            "password_hash": hash_password("admin123"),
            "role": "admin"
        }
    }
    save_users(seed_users)


def get_current_user(request: Request) -> Optional[dict]:
    session_data = request.session.get("user")
    if not session_data:
        return None

    users = load_users()
    user = users.get(session_data["email"])
    if not user:
        return None

    return {
        "email": session_data["email"],
        "role": user["role"],
    }


def require_auth(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(request: Request) -> dict:
    user = require_auth(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


ensure_users_file()

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/signup")
def signup(payload: SignUpRequest, request: Request):
    users = load_users()

    if payload.email in users:
        raise HTTPException(status_code=400, detail="Email is already registered")

    role = payload.role.lower()
    if role not in {"student", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    if role == "admin":
        current = get_current_user(request)
        if not current or current["role"] != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only admins can create admin accounts"
            )

    users[payload.email] = {
        "password_hash": hash_password(payload.password),
        "role": role,
    }
    save_users(users)

    return {"message": "Account created successfully", "email": payload.email, "role": role}


@app.post("/auth/login")
def login(payload: LoginRequest, request: Request):
    users = load_users()
    account = users.get(payload.email)

    if not account or account["password_hash"] != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    request.session["user"] = {
        "email": payload.email,
    }

    return {
        "message": "Logged in successfully",
        "user": {
            "email": payload.email,
            "role": account["role"],
        }
    }


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.get("/auth/me")
def me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}


@app.get("/admin/users")
def list_users(request: Request):
    require_admin(request)
    users = load_users()
    return {
        "users": [
            {"email": email, "role": details["role"]}
            for email, details in users.items()
        ]
    }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, request: Request):
    """Sign up current authenticated user for an activity."""
    current_user = require_auth(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]
    email = current_user["email"]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, request: Request, email: Optional[str] = None):
    """Unregister a student from an activity."""
    current_user = require_auth(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    target_email = email or current_user["email"]

    if current_user["role"] != "admin" and target_email != current_user["email"]:
        raise HTTPException(status_code=403, detail="You can only unregister yourself")

    # Validate student is signed up
    if target_email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(target_email)
    return {"message": f"Unregistered {target_email} from {activity_name}"}
