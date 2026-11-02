from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["restaurantDB"]

ingredients_collection = db["ingredients"]
dishes_collection = db["dishes"]