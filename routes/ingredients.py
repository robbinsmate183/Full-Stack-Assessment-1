
from flask import Blueprint, request, jsonify
from database import ingredients_collection
from routes.auth import token_required, admin_required
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, date, timedelta
import math 

ingredients_bp = Blueprint("ingredients", __name__)

required_fields = [
    "name",
    "stock_quantity",
    "unit",
    "purchase_cost",
    "supplier",
    "delivery_date",
    "expiry_date",
    "storage_location"
]


# Create Ingredient Function
@ingredients_bp.post("/ingredients")
@token_required
def add_ingredient():
    data = request.get_json()

    # Validation for ingredient data
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid ingredient data"}), 400

    missing_fields = []

    # Validation for required fields
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    stock_quantity = data["stock_quantity"]

    # Validation for stock quantity
    if (
        isinstance(stock_quantity, bool)
        or not isinstance(stock_quantity, (int, float))
        or stock_quantity < 0
    ):
        return jsonify({"error": "Invalid stock quantity"}), 400

    purchase_cost = data["purchase_cost"]

    # Validation for purchase cost
    if (
        isinstance(purchase_cost, bool)
        or not isinstance(purchase_cost, (int, float))
        or purchase_cost < 0
    ):
        return jsonify({"error": "Invalid purchase cost"}), 400

    result = ingredients_collection.insert_one(data)

    return jsonify({
        "message": "Ingredient added successfully",
        "id": str(result.inserted_id)
    }), 201





# Get All Ingredients Function
@ingredients_bp.get("/ingredients")
@token_required
def get_ingredients():

    search = request.args.get("search")
    supplier = request.args.get("supplier")
    storage_location = request.args.get("storage_location")

    sort_field = request.args.get("sort", "name")
    sort_order = request.args.get("order", "asc")

    allowed_sort_fields = ["name", "stock_quantity", "purchase_cost"]

    # Validation for sort field
    if sort_field not in allowed_sort_fields:
        return jsonify({"error": "Invalid sort field"}), 400

    # Validation for sort order
    if sort_order not in ["asc", "desc"]:
        return jsonify({"error": "Invalid sort order"}), 400

    direction = 1 if sort_order == "asc" else -1

    page_value = request.args.get("page", "1")
    limit_value = request.args.get("limit", "10")

    # Validation for page and limit values
    if not page_value.isdigit() or not limit_value.isdigit():
        return jsonify({"error": "Invalid page or limit"}), 400

    page = int(page_value)
    limit = int(limit_value)

    # Validation for pagination range
    if page < 1 or limit < 1 or limit > 100:
        return jsonify({"error": "Invalid page or limit"}), 400

    query = {}

    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    if supplier:
        query["supplier"] = supplier

    if storage_location:
        query["storage_location"] = storage_location

    total_records = ingredients_collection.count_documents(query)
    total_pages = (total_records + limit - 1) // limit

    skip = (page - 1) * limit

    ingredients = list(
        ingredients_collection.find(query)
        .sort(sort_field, direction)
        .skip(skip)
        .limit(limit)
    )

    for ingredient in ingredients:
        ingredient["_id"] = str(ingredient["_id"])

    return jsonify({
        "ingredients": ingredients,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }), 200


# Get Expiring Ingredients Function
@ingredients_bp.get("/ingredients/expiring")
@token_required
def get_expiring_ingredients():

    days_value = request.args.get("days", "7")

    # Validation for days value
    if not days_value.isdigit():
        return jsonify({"error": "Invalid days value"}), 400

    days = int(days_value)

    # Validation for date range
    try:
        today = date.today()
        cutoff_date = today + timedelta(days=days)
    except OverflowError:
        return jsonify({"error": "Invalid days value"}), 400

    ingredients = list(ingredients_collection.find())

    expiring_ingredients = []

    for ingredient in ingredients:

        # Validation for expiry date format
        try:
            expiry_date = datetime.strptime(
                ingredient["expiry_date"], "%d/%m/%Y"
            ).date()
        except (ValueError, TypeError, KeyError):
            continue

        if today <= expiry_date <= cutoff_date:
            ingredient["_id"] = str(ingredient["_id"])
            expiring_ingredients.append(ingredient)

    expiring_ingredients.sort(
        key=lambda ingredient: datetime.strptime(
            ingredient["expiry_date"], "%d/%m/%Y"
        )
    )

    return jsonify(expiring_ingredients), 200


# Get One Ingredient Function
@ingredients_bp.get("/ingredients/<ingredient_id>")
@token_required
def get_one_ingredient(ingredient_id):
    try:
        ingredient = ingredients_collection.find_one(
            {"_id": ObjectId(ingredient_id)}
        )

    # Validation for ingredient ID
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    # Validation for ingredient not found
    if ingredient is None:
        return jsonify({"error": "Ingredient not found"}), 404

    ingredient["_id"] = str(ingredient["_id"])
    return jsonify(ingredient), 200


# Update Ingredient Function
@ingredients_bp.patch("/ingredients/<ingredient_id>")
@token_required
def update_ingredient(ingredient_id):
    data = request.get_json()

    # Validation for update data
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "No update data provided"}), 400

    # Validation to prevent changing ingredient ID
    if "_id" in data:
        return jsonify({"error": "Cannot update ingredient ID"}), 400

    try:
        result = ingredients_collection.update_one(
            {"_id": ObjectId(ingredient_id)},
            {"$set": data}
        )

    # Validation for ingredient ID
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    # Validation for ingredient not found
    if result.matched_count == 0:
        return jsonify({"error": "Ingredient not found"}), 404

    return jsonify({"message": "Ingredient updated successfully"}), 200


# Delete Ingredient Function
@ingredients_bp.delete("/ingredients/<ingredient_id>")
@token_required
@admin_required
def delete_ingredient(ingredient_id):
    try:
        result = ingredients_collection.delete_one(
            {"_id": ObjectId(ingredient_id)}
        )

    # Validation for ingredient ID
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    # Validation for ingredient not found
    if result.deleted_count == 0:
        return jsonify({"error": "Ingredient not found"}), 404

    return jsonify({"message": "Ingredient deleted successfully"}), 200


# Get Low Stock Ingredients Function
@ingredients_bp.get("/ingredients/low-stock")
@token_required
def get_low_stock_ingredients():

    threshold_value = request.args.get("threshold", "10")

    # Validation for threshold value
    try:
        threshold = float(threshold_value)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid threshold"}), 400

    # Validation for negative or invalid threshold
    if not math.isfinite(threshold) or threshold < 0:
        return jsonify({"error": "Invalid threshold"}), 400

    query = {
        "stock_quantity": {"$lt": threshold}
    }

    ingredients = list(ingredients_collection.find(query))

    for ingredient in ingredients:
        ingredient["_id"] = str(ingredient["_id"])

    return jsonify(ingredients), 200
