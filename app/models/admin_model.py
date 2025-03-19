from pydantic import BaseModel


class AdminDetails(BaseModel):
    admin_name: str
    admin_email: str
    admin_contact: int
    admin_password: str


class AdminLogin(BaseModel):
    admin_id: str
    admin_password: str
