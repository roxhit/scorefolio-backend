from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router.pms_router import *
from app.router.admin_router import *
from app.router.company_router import *

# from app.routes.admin_router import *

app = FastAPI(title="Placement Management System", docs_url="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pms_route)
app.include_router(adminRouter, tags=["Admin Collection"])
app.include_router(companyRoute, tags=["Company Collection"])
# app.include_router(admin_route)
