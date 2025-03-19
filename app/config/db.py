from pymongo import MongoClient
import os
import cloudinary

MONGO_URL = "mongodb+srv://rohitsingh692004:gItvbSL4gGwtlXEb@cluster0.tac6wmj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URL)
database = client.minor_project
student_collection = database["student_collection"]
admin_collection = database["admin_collection"]
notifications_collection = database["notifications"]
companies_collection = database["companies_collection"]


# Cloudinary API Configuration
cloudinary.config(
    cloud_name="dhysz4sun",
    api_key="537939189425699",
    api_secret="Zu7Ss3Vjr2Y3NjIuaB3Ttb0lgeU",
)
