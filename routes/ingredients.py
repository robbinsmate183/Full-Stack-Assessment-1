from flask import Blueprint, request, jsonify
from database import ingredients_collection
from bson import ObjectId
from bson.errors import InvalidId

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

@ingredients_bp.post("/ingredients")
def add_ingredient():
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid ingredient data"}), 400

    missing_fields = []

    for field in required_fields:
        if field not in data:
            missing_fields.append(field)

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    stock_quantity = data["stock_quantity"]

    if (
        isinstance(stock_quantity, bool)
        or not isinstance(stock_quantity, (int, float))
        or stock_quantity < 0
    ):
        return jsonify({"error": "Invalid stock quantity"}), 400

    purchase_cost = data["purchase_cost"]

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

@ingredients_bp.get("/ingredients")
def get_ingredients():
    ingredients = list(ingredients_collection.find())

    for ingredient in ingredients:
        ingredient["_id"] = str(ingredient["_id"])

    return jsonify(ingredients), 200

@ingredients_bp.get("/ingredients/<ingredient_id>")
def get_one_ingredient(ingredient_id):
    try:
        ingredient = ingredients_collection.find_one({"_id": ObjectId(ingredient_id)})

    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    if ingredient is None:
        return jsonify({"error": "Ingredient not found"}), 404

    ingredient["_id"] = str(ingredient["_id"])
    return jsonify(ingredient), 200

@ingredients_bp.patch("/ingredients/<ingredient_id>")
def update_ingredient(ingredient_id):
    data = request.get_json()

    if not isinstance(data, dict) or not data:
        return jsonify({"error": "No update data provided"}), 400

    if "_id" in data:
        return jsonify({"error": "Cannot update ingredient ID"}), 400

    try:
        result = ingredients_collection.update_one(
            {"_id": ObjectId(ingredient_id)},
            {"$set": data}
        )

    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    if result.matched_count == 0:
        return jsonify({"error": "Ingredient not found"}), 404

    return jsonify({"message": "Ingredient updated successfully"}), 200

@ingredients_bp.delete("/ingredients/<ingredient_id>")
def delete_ingredient(ingredient_id):
    try:
        result = ingredients_collection.delete_one(
            {"_id": ObjectId(ingredient_id)}
        )

    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    if result.deleted_count == 0:
        return jsonify({"error": "Ingredient not found"}), 404

    return jsonify({"message": "Ingredient deleted successfully"}), 200