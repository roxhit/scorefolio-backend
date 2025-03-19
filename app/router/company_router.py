from fastapi import APIRouter, HTTPException, UploadFile
from app.config.db import *
from app.models.company_model import *
from bson import ObjectId
import cloudinary
import cloudinary.uploader

companyRoute = APIRouter()


@companyRoute.post("/add-company")
async def add_company(company_details: CompanyDetails):
    company_data = company_details.dict()
    result = companies_collection.insert_one(company_data)
    return {
        "message": "Company added successfully",
        "company_id": str(result.inserted_id),
    }


@companyRoute.put("/companies/{company_id}/logo", response_model=dict)
async def upload_logo(company_id: str, file: UploadFile):
    """
    Upload a logo to Cloudinary and update the company's logo URL in MongoDB.
    """
    try:
        # Upload logo to Cloudinary
        upload_result = cloudinary.uploader.upload(file.file, folder="company_logos")
        logo_url = upload_result.get("secure_url")
        if not logo_url:
            raise HTTPException(
                status_code=400, detail="Failed to upload logo to Cloudinary"
            )

        # Update MongoDB with the Cloudinary URL
        result = companies_collection.update_one(
            {"_id": ObjectId(company_id)}, {"$set": {"logo": logo_url}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Company not found")

        return {"message": "Logo updated successfully", "logo_url": logo_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@companyRoute.get("/companies/", response_model=dict)
def get_companies():
    companies = list(companies_collection.find())
    for company in companies:
        company["_id"] = str(company["_id"])
    return {"companies": companies}


@companyRoute.put("/companies/{company_id}", response_model=dict)
def update_company(company_id: str, updated_company: CompanyDetails):
    result = companies_collection.update_one(
        {"_id": ObjectId(company_id)}, {"$set": updated_company.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"message": "Company updated successfullcompanyRoute"}


# Delete a company
@companyRoute.delete("/companies/{company_id}", response_model=dict)
def delete_company(company_id: str):
    result = companies_collection.delete_one({"_id": ObjectId(company_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"message": "Company deleted successfully"}
