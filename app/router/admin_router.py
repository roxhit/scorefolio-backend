from fastapi import APIRouter, HTTPException, Body
from app.config.db import *
from app.models.admin_model import *
from bson import ObjectId  # Import password utilities
from passlib.context import CryptContext
import jwt  # Import for generating tokens
from datetime import datetime, timedelta
from typing import Optional

# Initialize the CryptContext with bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password.

    Args:
        password (str): Plain-text password.

    Returns:
        str: Hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against its hashed version.

    Args:
        plain_password (str): Plain-text password.
        hashed_password (str): Hashed password.

    Returns:
        bool: True if passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


adminRouter = APIRouter()


@adminRouter.post("/admin-register")
async def admin_register(admin_details: AdminDetails):
    """
    Registers a new admin.

    Args:
        admin_details (AdminDetails): Contains admin details like name, email, contact, and password.

    Returns:
        dict: Success message and the admin ID.

    Raises:
        HTTPException: If email already exists, phone number is invalid, or password is too short.
    """
    # Check if the email is already in use
    admin_present = admin_collection.find_one({"email": admin_details.admin_email})
    if admin_present:
        raise HTTPException(status_code=409, detail="Email already exists")

    # Validate contact number and password length
    if len(str(admin_details.admin_contact)) != 10:
        raise HTTPException(status_code=400, detail="Phone number must be 10 digits")
    if len(admin_details.admin_password) < 7:
        raise HTTPException(
            status_code=400, detail="Password must be at least 7 characters long"
        )

    # Hash the password before storing
    hashed_password = hash_password(admin_details.admin_password)
    admin_details_dict = dict(admin_details)
    admin_details_dict["admin_password"] = hashed_password

    # Insert into the database
    inserted_id = admin_collection.insert_one(admin_details_dict).inserted_id
    return {"message": "Admin registered successfully", "admin_id": str(inserted_id)}


# Secret key and algorithm for JWT
SECRET_KEY = "rohitsingh692004"  # Replace with a secure, random key
ALGORITHM = "HS256"  # Algorithm used for signing the token


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Generate a JWT access token.

    Args:
        data (dict): Data to include in the payload.
        expires_delta (timedelta, optional): Token expiration duration.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)  # Default: 1 hour
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@adminRouter.post("/admin-login")
async def admin_login(admin_details: AdminLogin):
    """
    Authenticates an admin based on their ID and password and returns an access token.

    Args:
        admin_details (AdminLogin): Contains admin ID and password.

    Returns:
        dict: Success message, admin details, and an access token.

    Raises:
        HTTPException: If admin ID is invalid or the password does not match.
    """
    # Fetch admin by ID
    admin_present = admin_collection.find_one({"_id": ObjectId(admin_details.admin_id)})
    if not admin_present:
        raise HTTPException(status_code=404, detail="Admin ID not found")

    # Verify the password
    if not verify_password(
        admin_details.admin_password, admin_present["admin_password"]
    ):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Generate access token
    token_data = {
        "admin_id": str(admin_present["_id"]),
        "admin_email": admin_present["admin_email"],
    }
    access_token = create_access_token(
        data=token_data, expires_delta=timedelta(hours=1)
    )

    # Return successful login details with token
    return {
        "message": "Login successful",
        "admin_name": admin_present["admin_name"],
        "admin_email": admin_present["admin_email"],
        "access_token": access_token,
    }


@adminRouter.get("/get-all-students")
async def get_all_students():
    """
    Fetch all students with their verification status,
    and return counts for total, verified, and not verified students.

    Returns:
        dict: List of all students and counts of verified/not verified students.
    """
    all_student_cursor = student_collection.find()
    all_students = []
    verified_count = 0
    not_verified_count = 0

    for student in all_student_cursor:
        student["_id"] = str(student["_id"])
        all_students.append(student)

        # Assuming there is a 'verified' field in the student document
        if student.get("is_verified", False):
            verified_count += 1
        else:
            not_verified_count += 1

    total_students = len(all_students)

    return {
        "total_students": total_students,
        "verified_students": verified_count,
        "not_verified_students": not_verified_count,
        "all_students": all_students,
    }


@adminRouter.get("/get-student-detail/{student_id}")
async def get_student_detail(student_id: str):
    student_present = student_collection.find_one({"student_id": student_id})
    if student_present:
        # Remove "_id" and "password" fields from the response
        student_present.pop("_id", None)
        student_present.pop("password", None)
        return student_present
    else:
        return {"message": "Student not found"}


@adminRouter.put("/verify-student/{student_id}")
async def verify_student(student_id: str):
    # Find the student in the collection
    student_present = student_collection.find_one({"student_id": student_id})
    if student_present:
        if not student_present.get("is_verified", False):
            # Update the is_verified field to true
            student_collection.update_one(
                {"student_id": student_id}, {"$set": {"is_verified": True}}
            )
            return {"message": f"Student with ID {student_id} has been verified."}
        else:
            return {"message": f"Student with ID {student_id} is already verified."}
    else:
        return {"message": "Student not found"}


@adminRouter.post("/send-notification")
async def send_notification(
    message: str = Body(..., embed=True),
    student_id: Optional[str] = Body(None, embed=True),
):
    """
    Send a notification to all students or a specific student.

    :param message: The notification message.
    :param student_id: (Optional) ID of a specific student. If "all", the notification is sent to all students.
    """
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    if student_id == "all":
        # Fetch all student IDs
        students = student_collection.find({}, {"student_id": 1, "_id": 0})
        student_ids = [student["student_id"] for student in students]

        if not student_ids:
            raise HTTPException(status_code=404, detail="No students found.")

        # Insert a notification for each student
        notifications = [
            {
                "message": message,
                "timestamp": datetime.utcnow(),
                "student_id": student_id,
            }
            for student_id in student_ids
        ]
        notifications_collection.insert_many(notifications)

        return {"message": "Notification sent to all students."}

    else:
        # Insert notification for a specific student
        notification = {
            "message": message,
            "timestamp": datetime.utcnow(),
            "student_id": student_id,
        }
        notifications_collection.insert_one(notification)
        return {"message": f"Notification sent to student with ID {student_id}."}
