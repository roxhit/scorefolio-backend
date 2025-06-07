from fastapi import APIRouter, HTTPException, Depends, Security, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from app.config.db import *
from app.models.pms_model import *
import re
from passlib.context import CryptContext
import random
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
from bson import ObjectId
from app.schemas.pms_schema import *

pms_route = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Secret key for JWT
SECRET_KEY = "rohitsingh"  # Change this to a random secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@pms_route.post("/student-signin")
async def student_signin(student_signin: AddStudent):
    """
    Registers a new student by validating their email, contact number,
    and hashing their password. Generates a unique 12-digit student ID
    starting with 'SSGI20' and saves the student's details in the database.

    Args:
    - student_signin (AddStudent): A Pydantic model that contains the student's name, email, password, and contact number.

    Raises:
    - HTTPException: If a student with the same email already exists or if the email/phone number is invalid.

    Returns:
    - JSON response with a success message and the generated student ID.
    """
    try:
        # Check if the student with the same email already exists
        student_present = student_collection.find_one({"email": student_signin.email})
        if student_present:
            raise HTTPException(
                status_code=400, detail="Student with that email already exists"
            )

        # Validate email format
        if not re.search(r"(\w{1,})@([a-z]+).([a-z]+)", student_signin.email):
            raise HTTPException(status_code=400, detail="Invalid Email Address")

        # Validate contact number length (e.g., must be 10 digits)
        if len(student_signin.contact) != 10 or not student_signin.contact.isdigit():
            raise HTTPException(
                status_code=400, detail="Invalid Contact Number. Must be 10 digits."
            )

        # Hash the password before saving it
        hashed_password = pwd_context.hash(student_signin.password)

        # Generate a 12-digit student ID starting with 'SSGI20'
        student_id = "SSGI20" + str(
            random.randint(100000, 999999)
        )  # Remaining 6 digits

        # Create new student entry
        new_student = {
            "student_id": student_id,
            "name": student_signin.name,
            "email": student_signin.email,
            "password": hashed_password,  # Store the hashed password
            "phone": student_signin.contact,
            "is_verified": False,
        }

        # Insert the student into the database
        student_collection.insert_one(new_student)

        return {"message": "Student registered successfully", "student_id": student_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


@pms_route.post("/student-login")
async def student_login(student_detail: StudentLogin):
    """
    Endpoint to authenticate a student using their student ID and password.

    Args:
        student_detail (StudentLogin): A Pydantic model containing the student_id and password.

    Returns:
        dict: A success message with the student's ID if login is successful.

    Raises:
        HTTPException:
            404: Raised if the student ID is not found in the database.
            401: Raised if the provided password does not match the stored hashed password.
            500: Raised if any internal server error occurs during the process.
    """
    try:
        # Check if student exists in the database
        student_present = student_collection.find_one(
            {"student_id": student_detail.student_id}
        )

        if not student_present:
            raise HTTPException(status_code=404, detail="Student not found")

        # Check if the password matches
        if not verify_password(student_detail.password, student_present["password"]):
            raise HTTPException(status_code=401, detail="Incorrect password")

        if student_present and verify_password(
            student_detail.password, student_present["password"]
        ):
            student_name = student_present.get("name", "Student")

        return {
            "message": "Login successful",
            "student_id": student_detail.student_id,
            "student_name": student_name,
            # Send the token back to the client
        }

    except HTTPException as http_err:
        # Rethrow known HTTP exceptions
        raise http_err

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pms_route.get("/student/verify-token/{token}")
async def verify_token(token: str):
    """
    Verifies a student's JWT token for authenticity and validity.

    Args:
        token (str): The JWT token to be verified.

    Returns:
        dict: Success message with the student ID if token is valid.

    Raises:
        HTTPException:
            401: Raised if the token is expired or invalid.
            500: Raised for any other internal server error.
    """
    try:
        # Decode the token to get the student ID and verify it hasn't expired
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id = payload.get("student_id")

        if not student_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Optionally, you can also check if the student exists in the database
        student_present = student_collection.find_one({"student_id": student_id})
        if not student_present:
            raise HTTPException(status_code=404, detail="Student not found")

        return {"message": "Token is valid", "student_id": student_id}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pms_route.post("/student-detail", tags=["Student Collection"])
async def create_student_detail(student_id: str, student_detail: StudentDetails):
    """
    API to create and save a student's basic details in MongoDB for a specific student_id.

    Args:
    - student_id (str): Unique ID of the student in MongoDB.
    - student_detail (StudentDetails): Basic details including 10th, 12th, and semester details.

    Returns:
    - JSON response with a success message if update is successful.
    """
    try:
        # Check if the student with the provided student_id exists
        student_present = student_collection.find_one({"student_id": student_id})
        if not student_present:
            raise HTTPException(status_code=404, detail="Student not found")

        # Prepare the data without marksheets
        student_data = {
            "basic_details": student_detail.basic_details.model_dump(
                exclude_defaults=True
            ),
            "tenth_details": student_detail.tenth_details.model_dump(
                exclude_defaults=True
            ),
            "twelfth_details": student_detail.twelfth_details.model_dump(
                exclude_defaults=True
            ),
            "semester_details": [
                semester.model_dump() for semester in student_detail.semester_details
            ],
        }

        # Update the student record with the new details
        update_result = student_collection.update_one(
            {"student_id": student_id}, {"$set": student_data}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500, detail="Failed to update student details"
            )

        return {
            "message": "Student details updated successfully",
            "student_id": student_id,
        }

    except HTTPException as http_err:
        raise http_err

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@pms_route.put("/upload-marksheets", tags=["Student Collection"])
async def upload_marksheets(
    student_id: str,
    tenth_marksheet: UploadFile = File(...),
    twelfth_marksheet: UploadFile = File(...),
    semester_marksheets: List[UploadFile] = File(...),
):
    try:
        # Fetch student document to ensure student exists
        student_doc = student_collection.find_one({"student_id": student_id})
        if not student_doc:
            raise HTTPException(
                status_code=404, detail="Student not found in the database"
            )

        # Function to upload files to Cloudinary
        def upload_file(file, folder_name):
            return cloudinary.uploader.upload(
                file.file, resource_type="auto", folder=folder_name
            )["secure_url"]

        # Upload files to Cloudinary
        tenth_url = upload_file(tenth_marksheet, "MinorProject/10th")
        twelfth_url = upload_file(twelfth_marksheet, "MinorProject/12th")
        semester_urls = [
            upload_file(sem, "MinorProject/Semesters") for sem in semester_marksheets
        ]

        # Aggregate update operation for MongoDB
        update_fields = {
            "tenth_details.marksheet_url": tenth_url,  # Removed .0 index
            "twelfth_details.marksheet_url": twelfth_url,  # Removed .0 index
            **{
                f"semester_details.{i}.marksheet_url": url
                for i, url in enumerate(semester_urls)
            },
        }

        # Execute update in a single operation
        update_result = student_collection.update_one(
            {"student_id": student_id}, {"$set": update_fields}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500, detail="Failed to update marksheets URLs."
            )

        return {
            "message": "Marksheets uploaded and URLs saved successfully",
            "marksheet_urls": {
                "tenth_marksheet_url": tenth_url,
                "twelfth_marksheet_url": twelfth_url,
                "semester_marksheets_urls": semester_urls,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@pms_route.get("/view-profile", tags=["Student Collection"])
async def view_profile(student_id: str):
    student_present = student_collection.find_one({"student_id": student_id})
    if not student_present:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"Student Detail": list_serial_student([student_present])}


@pms_route.get("/get-notifications/{student_id}")
async def get_notifications(student_id: str):
    """
    Get notifications for a specific student.

    :param student_id: The ID of the student fetching their notifications.
    :return: A list of notifications.
    """
    # Fetch notifications specific to the student or sent to "all"
    notifications = notifications_collection.find(
        {"$or": [{"student_id": student_id}, {"student_id": "all"}]}
    )

    notifications_list = [
        {"message": notification["message"], "timestamp": notification["timestamp"]}
        for notification in notifications
    ]

    if not notifications_list:
        return {"message": "No notifications found."}

    return {"notifications": notifications_list}


@pms_route.put("/update-profile", tags=["Student Profile"])
async def update_profile(student_id: str, profile_updates: UpdateProfile):
    """
    Update a student's profile details in MongoDB.

    Args:
    - student_id (str): Unique identifier of the student.
    - profile_updates (UpdateProfile): The updated profile details.

    Returns:
    - JSON response indicating success or failure.
    """
    try:
        # Check if student exists
        student_present = student_collection.find_one({"student_id": student_id})
        if not student_present:
            raise HTTPException(status_code=404, detail="Student not found")

        # Prepare update data
        update_data = {}
        if profile_updates.basic_details:
            update_data["basic_details"] = profile_updates.basic_details.dict(
                exclude_unset=True
            )
        if profile_updates.tenth_details:
            update_data["tenth_details"] = profile_updates.tenth_details.dict(
                exclude_unset=True
            )
        if profile_updates.twelfth_details:
            update_data["twelfth_details"] = profile_updates.twelfth_details.dict(
                exclude_unset=True
            )
        if profile_updates.semester_details:
            update_data["semester_details"] = [
                sem.dict(exclude_unset=True) for sem in profile_updates.semester_details
            ]

        # Perform the update
        update_result = student_collection.update_one(
            {"student_id": student_id}, {"$set": update_data}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=400, detail="No changes were made to the student profile"
            )

        return {
            "message": "Student profile updated successfully",
            "student_id": student_id,
        }

    except HTTPException as http_err:
        raise http_err

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
