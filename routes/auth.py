from flask import Blueprint, request, jsonify
from database import users_collection
from dotenv import load_dotenv
from functools import wraps
import jwt, bcrypt, datetime, os



load_dotenv()

auth_bp = Blueprint("auth", __name__)


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


def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        token = request.headers.get("x-access-token")

        if not token:
            return jsonify({"error": "Token is missing"}), 401

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


def admin_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        token = request.headers.get("x-access-token")

        data = jwt.decode(
            token,
            os.getenv("SECRET_KEY"),
            algorithms=["HS256"]
        )

        if data["role"] != "admin":
            return jsonify({"error": "Admin access required"}), 403
      
        return f(*args, **kwargs)

    return decorated

