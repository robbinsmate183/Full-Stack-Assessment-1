
from flask import Blueprint, request, jsonify
from database import users_collection
from dotenv import load_dotenv
from bson import ObjectId
from functools import wraps
import jwt, bcrypt, datetime, os

load_dotenv()

auth_bp = Blueprint("auth", __name__)


# Login Function
@auth_bp.post("/login")
def login():

    auth = request.authorization

    if auth:

        user = users_collection.find_one({
            "username": auth.username
        })

        if user is not None:

            if bcrypt.checkpw(
                bytes(auth.password, "UTF-8"),
                user["password"]
            ):

                token = jwt.encode(
                    {
                        "user": auth.username,
                        "role": user["role"],
                        "exp": datetime.datetime.now(datetime.UTC)
                               + datetime.timedelta(hours=2)
                    },
                    os.getenv("SECRET_KEY"),
                    algorithm="HS256"
                )

                return jsonify({"token": token}), 200

    return jsonify({"error": "Invalid username or password"}), 401


# Check User Token Function
def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        token = request.headers.get("x-access-token")

        # Validation for missing token
        if not token:
            return jsonify({"error": "Token is missing"}), 401

        # Validation for expired or invalid token
        try:
            data = jwt.decode(
                token,
                os.getenv("SECRET_KEY"),
                algorithms=["HS256"]
            )

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401

        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated


# Check Admin Access Function
def admin_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        token = request.headers.get("x-access-token")

        data = jwt.decode(
            token,
            os.getenv("SECRET_KEY"),
            algorithms=["HS256"]
        )

        # Validation for admin role
        if data.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return decorated


# Create User Function
@auth_bp.post("/users")
@token_required
@admin_required
def create_user():

    data = request.get_json(silent=True)

    # Validation for data being inputted 
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid user data"}), 400

    required_fields = ["username", "password", "role"]

    # Validation for required fields
    for field in required_fields:
        if field not in data:
            return jsonify({"error": "Missing required field", "field": field}), 400

    username = data["username"]
    password = data["password"]
    role = data["role"]

    # Validation for username
    if not isinstance(username, str) or not username.strip():
        return jsonify({"error": "Invalid username"}), 400

    username = username.strip()

    # Validation for password
    if not isinstance(password, str) or not password or len(password.encode("utf-8")) > 72:
        return jsonify({"error": "Invalid password"}), 400

    # Validation for user role
    if not isinstance(role, str) or role not in ["staff", "admin"]:
        return jsonify({"error": "Invalid role"}), 400

    existing_user = users_collection.find_one({"username": username})

    # Validation for existing username
    if existing_user is not None:
        return jsonify({"error": "Username already exists"}), 409

    hashed_password = bcrypt.hashpw(
        bytes(password, "UTF-8"),
        bcrypt.gensalt()
    )

    result = users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "role": role
    })

    return jsonify({
        "message": "User created successfully",
        "id": str(result.inserted_id)
    }), 201



# Get All Users Function
@auth_bp.get("/users")
@token_required
@admin_required
def get_users():

    users = list(users_collection.find({}, {"password": 0}))

    for user in users:
        user["_id"] = str(user["_id"])

    return jsonify(users), 200


# Get One User Function
@auth_bp.get("/users/<user_id>")
@token_required
@admin_required
def get_one_user(user_id):

    # Validation for user ID
    if not ObjectId.is_valid(user_id):
        return jsonify({"error": "Invalid user ID"}), 400

    user = users_collection.find_one(
        {"_id": ObjectId(user_id)},
        {"password": 0}
    )

    # Validation for user not found
    if user is None:
        return jsonify({"error": "User not found"}), 404

    user["_id"] = str(user["_id"])

    return jsonify(user), 200


# Update User Function
@auth_bp.patch("/users/<user_id>")
@token_required
@admin_required
def update_user(user_id):

    # Validation for user ID
    if not ObjectId.is_valid(user_id):
        return jsonify({"error": "Invalid user ID"}), 400

    data = request.get_json(silent=True)

    # Validation for update data
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "No update data provided"}), 400

    allowed_fields = ["username", "password", "role"]

    # Validation for allowed fields
    for field in data:
        if field not in allowed_fields:
            return jsonify({"error": "Invalid field", "field": field}), 400

    user = users_collection.find_one({"_id": ObjectId(user_id)})

    # Validation for user not found
    if user is None:
        return jsonify({"error": "User not found"}), 404

    if "username" in data:

        # Validation for username
        if not isinstance(data["username"], str) or not data["username"].strip():
            return jsonify({"error": "Invalid username"}), 400

        data["username"] = data["username"].strip()

        existing_user = users_collection.find_one({
            "username": data["username"]
        })

        # Validation for existing username
        if existing_user is not None and existing_user["_id"] != user["_id"]:
            return jsonify({"error": "Username already exists"}), 409

    if "password" in data:

        password = data["password"]

        # Validation for password
        if not isinstance(password, str) or not password or len(password.encode("utf-8")) > 72:
            return jsonify({"error": "Invalid password"}), 400

        data["password"] = bcrypt.hashpw(
            bytes(password, "UTF-8"),
            bcrypt.gensalt()
        )

    if "role" in data:

        # Validation for user role
        if not isinstance(data["role"], str) or data["role"] not in ["staff", "admin"]:
            return jsonify({"error": "Invalid role"}), 400

        # Validation to prevent removing the last admin role
        if user["role"] == "admin" and data["role"] == "staff":

            admin_count = users_collection.count_documents({"role": "admin"})

            if admin_count <= 1:
                return jsonify({"error": "Cannot demote the last admin"}), 403

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": data}
    )

    return jsonify({"message": "User updated successfully"}), 200

# Delete User Function
@auth_bp.delete("/users/<user_id>")
@token_required
@admin_required
def delete_user(user_id):

    # Validation for user ID
    if not ObjectId.is_valid(user_id):
        return jsonify({"error": "Invalid user ID"}), 400

    user = users_collection.find_one({"_id": ObjectId(user_id)})

    # Validation for user not found
    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Validation to prevent deleting the last admin
    if user["role"] == "admin":

        admin_count = users_collection.count_documents({"role": "admin"})

        if admin_count <= 1:
            return jsonify({"error": "Cannot delete the last admin"}), 403

    users_collection.delete_one({"_id": ObjectId(user_id)})

    return jsonify({"message": "User deleted successfully"}), 200
