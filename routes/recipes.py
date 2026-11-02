
from flask import Blueprint, request, jsonify
from database import dishes_collection, ingredients_collection
from bson import ObjectId
from bson.errors import InvalidId

dishes_bp = Blueprint("dishes", __name__)

required_fields = [
    "name",
    "category",
    "selling_price",
    "ingredients"
]

ingredient_required_fields = [
    "ingredient_id",
    "ingredient_name",
    "quantity",
    "unit"
]


@dishes_bp.post("/dishes")
def add_dish():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid dish data"}), 400

    missing_fields = []

    for field in required_fields:
        if field not in data:
            missing_fields.append(field)

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    if not isinstance(data["name"], str) or not data["name"].strip():
        return jsonify({"error": "Invalid dish name"}), 400

    if not isinstance(data["category"], str) or not data["category"].strip():
        return jsonify({"error": "Invalid dish category"}), 400

    selling_price = data["selling_price"]

    if (
        isinstance(selling_price, bool)
        or not isinstance(selling_price, (int, float))
        or selling_price <= 0
    ):
        return jsonify({"error": "Invalid selling price"}), 400

    ingredients = data["ingredients"]

    if not isinstance(ingredients, list) or not ingredients:
        return jsonify({
            "error": "Ingredients must be a non-empty list"
        }), 400

    for ingredient in ingredients:
        if not isinstance(ingredient, dict):
            return jsonify({"error": "Invalid ingredient entry"}), 400

        for field in ingredient_required_fields:
            if field not in ingredient:
                return jsonify({
                    "error": "Missing ingredient field",
                    "field": field
                }), 400

        if (
            not isinstance(ingredient["ingredient_name"], str)
            or not ingredient["ingredient_name"].strip()
        ):
            return jsonify({"error": "Invalid ingredient name"}), 400

        if (
            not isinstance(ingredient["unit"], str)
            or not ingredient["unit"].strip()
        ):
            return jsonify({"error": "Invalid ingredient unit"}), 400

        quantity = ingredient["quantity"]

        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, (int, float))
            or quantity <= 0
        ):
            return jsonify({"error": "Invalid ingredient quantity"}), 400

        ingredient_id = ingredient["ingredient_id"]

        try:
            mongo_id = ObjectId(ingredient_id)
        except (InvalidId, TypeError):
            return jsonify({"error": "Invalid ingredient ID"}), 400

        existing_ingredient = ingredients_collection.find_one(
            {"_id": mongo_id}
        )

        if existing_ingredient is None:
            return jsonify({"error": "Ingredient not found"}), 404

    result = dishes_collection.insert_one(data)

    return jsonify({
        "message": "Dish added successfully",
        "id": str(result.inserted_id)
    }), 201


@dishes_bp.get("/dishes")
def get_dishes():
    dishes = list(dishes_collection.find())

    for dish in dishes:
        dish["_id"] = str(dish["_id"])

    return jsonify(dishes), 200


@dishes_bp.get("/dishes/<dish_id>")
def get_one_dish(dish_id):
    try:
        dish = dishes_collection.find_one(
            {"_id": ObjectId(dish_id)}
        )
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid dish ID"}), 400

    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    dish["_id"] = str(dish["_id"])

    return jsonify(dish), 200


@dishes_bp.patch("/dishes/<dish_id>")
def update_dish(dish_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({"error": "No update data provided"}), 400

    if "_id" in data:
        return jsonify({"error": "Cannot update dish ID"}), 400

    if "name" in data:
        if not isinstance(data["name"], str) or not data["name"].strip():
            return jsonify({"error": "Invalid dish name"}), 400

    if "category" in data:
        if not isinstance(data["category"], str) or not data["category"].strip():
            return jsonify({"error": "Invalid dish category"}), 400

    if "selling_price" in data:
        selling_price = data["selling_price"]

        if (
            isinstance(selling_price, bool)
            or not isinstance(selling_price, (int, float))
            or selling_price <= 0
        ):
            return jsonify({"error": "Invalid selling price"}), 400

    if "ingredients" in data:
        ingredients = data["ingredients"]

        if not isinstance(ingredients, list) or not ingredients:
            return jsonify({
                "error": "Ingredients must be a non-empty list"
            }), 400

        for ingredient in ingredients:
            if not isinstance(ingredient, dict):
                return jsonify({"error": "Invalid ingredient entry"}), 400

            for field in ingredient_required_fields:
                if field not in ingredient:
                    return jsonify({
                        "error": "Missing ingredient field",
                        "field": field
                    }), 400

            if (
                not isinstance(ingredient["ingredient_name"], str)
                or not ingredient["ingredient_name"].strip()
            ):
                return jsonify({"error": "Invalid ingredient name"}), 400

            if (
                not isinstance(ingredient["unit"], str)
                or not ingredient["unit"].strip()
            ):
                return jsonify({"error": "Invalid ingredient unit"}), 400

            quantity = ingredient["quantity"]

            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, (int, float))
                or quantity <= 0
            ):
                return jsonify({"error": "Invalid ingredient quantity"}), 400

            ingredient_id = ingredient["ingredient_id"]

            try:
                mongo_id = ObjectId(ingredient_id)
            except (InvalidId, TypeError):
                return jsonify({"error": "Invalid ingredient ID"}), 400

            existing_ingredient = ingredients_collection.find_one(
                {"_id": mongo_id}
            )

            if existing_ingredient is None:
                return jsonify({"error": "Ingredient not found"}), 404

    try:
        result = dishes_collection.update_one(
            {"_id": ObjectId(dish_id)},
            {"$set": data}
        )
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid dish ID"}), 400

    if result.matched_count == 0:
        return jsonify({"error": "Dish not found"}), 404

    return jsonify({
        "message": "Dish updated successfully"
    }), 200


@dishes_bp.delete("/dishes/<dish_id>")
def delete_dish(dish_id):
    try:
        result = dishes_collection.delete_one(
            {"_id": ObjectId(dish_id)}
        )
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid dish ID"}), 400

    if result.deleted_count == 0:
        return jsonify({"error": "Dish not found"}), 404

    return jsonify({
        "message": "Dish deleted successfully"
    }), 200
