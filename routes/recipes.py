from flask import Blueprint, request, jsonify
from database import dishes_collection, ingredients_collection
from routes.auth import token_required, admin_required
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
@token_required
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

        ingredient["_id"] = str(ObjectId())

    result = dishes_collection.insert_one(data)

    return jsonify({
        "message": "Dish added successfully",
        "id": str(result.inserted_id)
    }), 201


@dishes_bp.get("/dishes")
@token_required
def get_dishes():

    search = request.args.get("search")
    category = request.args.get("category")

    sort_field = request.args.get("sort", "name")
    sort_order = request.args.get("order", "asc")

    allowed_sort_fields = ["name", "selling_price"]

    if sort_field not in allowed_sort_fields:
        return jsonify({"error": "Invalid sort field"}), 400

    if sort_order not in ["asc", "desc"]:
        return jsonify({"error": "Invalid sort order"}), 400

    direction = 1 if sort_order == "asc" else -1

    page_value = request.args.get("page", "1")
    limit_value = request.args.get("limit", "10")

    if not page_value.isdigit() or not limit_value.isdigit():
        return jsonify({"error": "Invalid page or limit"}), 400

    page = int(page_value)
    limit = int(limit_value)

    if page < 1 or limit < 1 or limit > 100:
        return jsonify({"error": "Invalid page or limit"}), 400

    query = {}

    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    if category:
        query["category"] = category

    total_records = dishes_collection.count_documents(query)
    total_pages = (total_records + limit - 1) // limit

    skip = (page - 1) * limit

    dishes = list(
        dishes_collection.find(query)
        .sort(sort_field, direction)
        .skip(skip)
        .limit(limit)
    )

    for dish in dishes:
        dish["_id"] = str(dish["_id"])

        for ingredient in dish.get("ingredients", []):
            if "_id" in ingredient:
                ingredient["_id"] = str(ingredient["_id"])

    return jsonify({
        "dishes": dishes,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }), 200


@dishes_bp.get("/dishes/<dish_id>")
@token_required
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

    for ingredient in dish.get("ingredients", []):
        if "_id" in ingredient:
            ingredient["_id"] = str(ingredient["_id"])

    return jsonify(dish), 200


@dishes_bp.patch("/dishes/<dish_id>")
@token_required
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

            ingredient["_id"] = str(ObjectId())

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
@token_required
@admin_required
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


@dishes_bp.post("/dishes/<dish_id>/ingredients")
@token_required
def add_dish_ingredient(dish_id):

    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid ingredient data"}), 400

    for field in ingredient_required_fields:
        if field not in data:
            return jsonify({
                "error": "Missing ingredient field",
                "field": field
            }), 400

    if (
        not isinstance(data["ingredient_name"], str)
        or not data["ingredient_name"].strip()
    ):
        return jsonify({"error": "Invalid ingredient name"}), 400

    if (
        not isinstance(data["unit"], str)
        or not data["unit"].strip()
    ):
        return jsonify({"error": "Invalid ingredient unit"}), 400

    quantity = data["quantity"]

    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, (int, float))
        or quantity <= 0
    ):
        return jsonify({"error": "Invalid ingredient quantity"}), 400

    ingredient_id = data["ingredient_id"]

    try:
        mongo_id = ObjectId(ingredient_id)
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    existing_ingredient = ingredients_collection.find_one({
        "_id": mongo_id
    })

    if existing_ingredient is None:
        return jsonify({"error": "Ingredient not found"}), 404

    new_ingredient = {
        "_id": str(ObjectId()),
        "ingredient_id": ingredient_id,
        "ingredient_name": data["ingredient_name"],
        "quantity": data["quantity"],
        "unit": data["unit"]
    }

    dishes_collection.update_one(
        {"_id": ObjectId(dish_id)},
        {"$push": {"ingredients": new_ingredient}}
    )

    return jsonify({
        "message": "Ingredient added to dish successfully",
        "id": new_ingredient["_id"]
    }), 201


@dishes_bp.get("/dishes/<dish_id>/ingredients")
@token_required
def get_dish_ingredients(dish_id):

    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    dish = dishes_collection.find_one(
        {"_id": ObjectId(dish_id)},
        {"ingredients": 1, "_id": 0}
    )

    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    ingredients = dish.get("ingredients", [])

    for ingredient in ingredients:
        if "_id" in ingredient:
            ingredient["_id"] = str(ingredient["_id"])

    return jsonify(ingredients), 200


@dishes_bp.get("/dishes/<dish_id>/ingredients/<entry_id>")
@token_required
def get_one_dish_ingredient(dish_id, entry_id):

    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    if not ObjectId.is_valid(entry_id):
        return jsonify({"error": "Invalid embedded ingredient ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    for ingredient in dish.get("ingredients", []):
        if str(ingredient.get("_id")) == entry_id:

            ingredient["_id"] = str(ingredient["_id"])

            return jsonify(ingredient), 200

    return jsonify({"error": "Embedded ingredient not found"}), 404


@dishes_bp.patch("/dishes/<dish_id>/ingredients/<entry_id>")
@token_required
def update_dish_ingredient(dish_id, entry_id):

    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    if not ObjectId.is_valid(entry_id):
        return jsonify({"error": "Invalid embedded ingredient ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    existing_entry = None

    for ingredient in dish.get("ingredients", []):
        if str(ingredient.get("_id")) == entry_id:
            existing_entry = ingredient
            break

    if existing_entry is None:
        return jsonify({"error": "Embedded ingredient not found"}), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({"error": "No update data provided"}), 400

    allowed_fields = [
        "ingredient_id",
        "ingredient_name",
        "quantity",
        "unit"
    ]

    for field in data:
        if field not in allowed_fields:
            return jsonify({"error": "Invalid update field"}), 400

    if "ingredient_name" in data:
        if (
            not isinstance(data["ingredient_name"], str)
            or not data["ingredient_name"].strip()
        ):
            return jsonify({"error": "Invalid ingredient name"}), 400

    if "unit" in data:
        if (
            not isinstance(data["unit"], str)
            or not data["unit"].strip()
        ):
            return jsonify({"error": "Invalid ingredient unit"}), 400

    if "quantity" in data:
        quantity = data["quantity"]

        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, (int, float))
            or quantity <= 0
        ):
            return jsonify({"error": "Invalid ingredient quantity"}), 400

    if "ingredient_id" in data:
        ingredient_id = data["ingredient_id"]

        try:
            mongo_id = ObjectId(ingredient_id)
        except (InvalidId, TypeError):
            return jsonify({"error": "Invalid ingredient ID"}), 400

        existing_ingredient = ingredients_collection.find_one({
            "_id": mongo_id
        })

        if existing_ingredient is None:
            return jsonify({"error": "Ingredient not found"}), 404

    update_data = {}

    for field in data:
        update_data["ingredients.$." + field] = data[field]

    result = dishes_collection.update_one(
        {
            "_id": ObjectId(dish_id),
            "ingredients._id": existing_entry["_id"]
        },
        {
            "$set": update_data
        }
    )

    if result.matched_count == 0:
        return jsonify({"error": "Embedded ingredient not found"}), 404

    return jsonify({
        "message": "Embedded ingredient updated successfully"
    }), 200


@dishes_bp.delete("/dishes/<dish_id>/ingredients/<entry_id>")
@token_required
@admin_required
def delete_dish_ingredient(dish_id, entry_id):

    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    if not ObjectId.is_valid(entry_id):
        return jsonify({"error": "Invalid embedded ingredient ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    existing_entry = None

    for ingredient in dish.get("ingredients", []):
        if str(ingredient.get("_id")) == entry_id:
            existing_entry = ingredient
            break

    if existing_entry is None:
        return jsonify({"error": "Embedded ingredient not found"}), 404

    result = dishes_collection.update_one(
        {"_id": ObjectId(dish_id)},
        {
            "$pull": {
                "ingredients": {
                    "_id": existing_entry["_id"]
                }
            }
        }
    )

    if result.modified_count == 0:
        return jsonify({"error": "Embedded ingredient not found"}), 404

    return jsonify({
        "message": "Embedded ingredient deleted successfully"
    }), 200
