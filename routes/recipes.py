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


# Create Dish Function
@dishes_bp.post("/dishes")
@token_required
def add_dish():
    data = request.get_json(silent=True)

    # Validation for data being inputted
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid dish data"}), 400

    missing_fields = []

    for field in required_fields:
        # Validation for required ingredient fields
        if field not in data:
            missing_fields.append(field)

    # Validation for required fields
    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    # Validation for dish name
    if not isinstance(data["name"], str) or not data["name"].strip():
        return jsonify({"error": "Invalid dish name"}), 400

    # Validation for dish category
    if not isinstance(data["category"], str) or not data["category"].strip():
        return jsonify({"error": "Invalid dish category"}), 400

    selling_price = data["selling_price"]

    # Validation for selling price
    if (
        isinstance(selling_price, bool)
        or not isinstance(selling_price, (int, float))
        or selling_price <= 0
    ):
        return jsonify({"error": "Invalid selling price"}), 400

    ingredients = data["ingredients"]

    # Validation for ingredients list
    if not isinstance(ingredients, list) or not ingredients:
        return jsonify({
            "error": "Ingredients must be a non-empty list"
        }), 400

    for ingredient in ingredients:
        # Validation for ingredient data
        if not isinstance(ingredient, dict):
            return jsonify({"error": "Invalid ingredient entry"}), 400

        for field in ingredient_required_fields:
            # Validation for required ingredient fields
            if field not in ingredient:
                return jsonify({
                    "error": "Missing ingredient field",
                    "field": field
                }), 400

        # Validation for ingredient name
        if (
            not isinstance(ingredient["ingredient_name"], str)
            or not ingredient["ingredient_name"].strip()
        ):
            return jsonify({"error": "Invalid ingredient name"}), 400

        # Validation for ingredient unit
        if (
            not isinstance(ingredient["unit"], str)
            or not ingredient["unit"].strip()
        ):
            return jsonify({"error": "Invalid ingredient unit"}), 400

        quantity = ingredient["quantity"]

        # Validation for ingredient quantity
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, (int, float))
            or quantity <= 0
        ):
            return jsonify({"error": "Invalid ingredient quantity"}), 400

        ingredient_id = ingredient["ingredient_id"]

        try:
            mongo_id = ObjectId(ingredient_id)
        # Validation for invalid ID
        except (InvalidId, TypeError):
            return jsonify({"error": "Invalid ingredient ID"}), 400

        existing_ingredient = ingredients_collection.find_one(
            {"_id": mongo_id}
        )

        # Validation for ingredient not found
        if existing_ingredient is None:
            return jsonify({"error": "Ingredient not found"}), 404

        ingredient["_id"] = str(ObjectId())

    result = dishes_collection.insert_one(data)

    return jsonify({
        "message": "Dish added successfully",
        "id": str(result.inserted_id)
    }), 201


# Get All Dishes Function
@dishes_bp.get("/dishes")
@token_required
def get_dishes():

    search = request.args.get("search")
    category = request.args.get("category")

    sort_field = request.args.get("sort", "name")
    sort_order = request.args.get("order", "asc")

    allowed_sort_fields = ["name", "selling_price"]

    # Validation for sort field
    if sort_field not in allowed_sort_fields:
        return jsonify({"error": "Invalid sort field"}), 400

    # Validation for sort order
    if sort_order not in ["asc", "desc"]:
        return jsonify({"error": "Invalid sort order"}), 400

    direction = 1 if sort_order == "asc" else -1

    page_value = request.args.get("page", "1")
    limit_value = request.args.get("limit", "10")

    # Validation for page and limit
    if not page_value.isdigit() or not limit_value.isdigit():
        return jsonify({"error": "Invalid page or limit"}), 400

    page = int(page_value)
    limit = int(limit_value)

    # Validation for page and limit
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


# Get One Dish Function
@dishes_bp.get("/dishes/<dish_id>")
@token_required
def get_one_dish(dish_id):
    try:
        dish = dishes_collection.find_one(
            {"_id": ObjectId(dish_id)}
        )
    # Validation for invalid ID
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid dish ID"}), 400

    # Validation for dish not found
    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    dish["_id"] = str(dish["_id"])

    for ingredient in dish.get("ingredients", []):
        if "_id" in ingredient:
            ingredient["_id"] = str(ingredient["_id"])

    return jsonify(dish), 200


# Update Dish Function
@dishes_bp.patch("/dishes/<dish_id>")
@token_required
def update_dish(dish_id):
    data = request.get_json(silent=True)

    # Validation for update data
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "No update data provided"}), 400

    # Validation for changing dish ID
    if "_id" in data:
        return jsonify({"error": "Cannot update dish ID"}), 400

    # Validation for dish name
    if "name" in data:
        # Validation for dish name
        if not isinstance(data["name"], str) or not data["name"].strip():
            return jsonify({"error": "Invalid dish name"}), 400

    # Validation for dish category
    if "category" in data:
        # Validation for dish category
        if not isinstance(data["category"], str) or not data["category"].strip():
            return jsonify({"error": "Invalid dish category"}), 400

    # Validation for selling price
    if "selling_price" in data:
        selling_price = data["selling_price"]

        # Validation for selling price
        if (
            isinstance(selling_price, bool)
            or not isinstance(selling_price, (int, float))
            or selling_price <= 0
        ):
            return jsonify({"error": "Invalid selling price"}), 400

    # Validation for ingredients list
    if "ingredients" in data:
        ingredients = data["ingredients"]

        # Validation for ingredients list
        if not isinstance(ingredients, list) or not ingredients:
            return jsonify({
                "error": "Ingredients must be a non-empty list"
            }), 400

        for ingredient in ingredients:
            # Validation for ingredient data
            if not isinstance(ingredient, dict):
                return jsonify({"error": "Invalid ingredient entry"}), 400

            for field in ingredient_required_fields:
                # Validation for required ingredient fields
                if field not in ingredient:
                    return jsonify({
                        "error": "Missing ingredient field",
                        "field": field
                    }), 400

            # Validation for ingredient name
            if (
                not isinstance(ingredient["ingredient_name"], str)
                or not ingredient["ingredient_name"].strip()
            ):
                return jsonify({"error": "Invalid ingredient name"}), 400

            # Validation for ingredient unit
            if (
                not isinstance(ingredient["unit"], str)
                or not ingredient["unit"].strip()
            ):
                return jsonify({"error": "Invalid ingredient unit"}), 400

            quantity = ingredient["quantity"]

            # Validation for ingredient quantity
            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, (int, float))
                or quantity <= 0
            ):
                return jsonify({"error": "Invalid ingredient quantity"}), 400

            ingredient_id = ingredient["ingredient_id"]

            try:
                mongo_id = ObjectId(ingredient_id)
            # Validation for invalid ID
            except (InvalidId, TypeError):
                return jsonify({"error": "Invalid ingredient ID"}), 400

            existing_ingredient = ingredients_collection.find_one(
                {"_id": mongo_id}
            )

            # Validation for ingredient not found
            if existing_ingredient is None:
                return jsonify({"error": "Ingredient not found"}), 404

            ingredient["_id"] = str(ObjectId())

    try:
        result = dishes_collection.update_one(
            {"_id": ObjectId(dish_id)},
            {"$set": data}
        )
    # Validation for invalid ID
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid dish ID"}), 400

    # Validation for record not found
    if result.matched_count == 0:
        return jsonify({"error": "Dish not found"}), 404

    return jsonify({
        "message": "Dish updated successfully"
    }), 200


# Delete Dish Function
@dishes_bp.delete("/dishes/<dish_id>")
@token_required
@admin_required
def delete_dish(dish_id):
    try:
        result = dishes_collection.delete_one(
            {"_id": ObjectId(dish_id)}
        )
    # Validation for invalid ID
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid dish ID"}), 400

    # Validation for dish not found
    if result.deleted_count == 0:
        return jsonify({"error": "Dish not found"}), 404

    return jsonify({
        "message": "Dish deleted successfully"
    }), 200


# Add Ingredient To Dish Function
@dishes_bp.post("/dishes/<dish_id>/ingredients")
@token_required
def add_dish_ingredient(dish_id):

    # Validation for dish ID
    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    # Validation for dish not found
    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    data = request.get_json(silent=True)

    # Validation for data being inputted
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid ingredient data"}), 400

    for field in ingredient_required_fields:
        # Validation for required ingredient fields
        if field not in data:
            return jsonify({
                "error": "Missing ingredient field",
                "field": field
            }), 400

    # Validation for ingredient name
    if (
        not isinstance(data["ingredient_name"], str)
        or not data["ingredient_name"].strip()
    ):
        return jsonify({"error": "Invalid ingredient name"}), 400

    # Validation for ingredient unit
    if (
        not isinstance(data["unit"], str)
        or not data["unit"].strip()
    ):
        return jsonify({"error": "Invalid ingredient unit"}), 400

    quantity = data["quantity"]

    # Validation for ingredient quantity
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, (int, float))
        or quantity <= 0
    ):
        return jsonify({"error": "Invalid ingredient quantity"}), 400

    ingredient_id = data["ingredient_id"]

    try:
        mongo_id = ObjectId(ingredient_id)
    # Validation for invalid ID
    except (InvalidId, TypeError):
        return jsonify({"error": "Invalid ingredient ID"}), 400

    existing_ingredient = ingredients_collection.find_one({
        "_id": mongo_id
    })

    # Validation for ingredient not found
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


# Get Dish Ingredients Function
@dishes_bp.get("/dishes/<dish_id>/ingredients")
@token_required
def get_dish_ingredients(dish_id):

    # Validation for dish ID
    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    dish = dishes_collection.find_one(
        {"_id": ObjectId(dish_id)},
        {"ingredients": 1, "_id": 0}
    )

    # Validation for dish not found
    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    ingredients = dish.get("ingredients", [])

    for ingredient in ingredients:
        if "_id" in ingredient:
            ingredient["_id"] = str(ingredient["_id"])

    return jsonify(ingredients), 200


# Get One Dish Ingredient Function
@dishes_bp.get("/dishes/<dish_id>/ingredients/<entry_id>")
@token_required
def get_one_dish_ingredient(dish_id, entry_id):

    # Validation for dish ID
    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    # Validation for embedded ingredient ID
    if not ObjectId.is_valid(entry_id):
        return jsonify({"error": "Invalid embedded ingredient ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    # Validation for dish not found
    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    for ingredient in dish.get("ingredients", []):
        if str(ingredient.get("_id")) == entry_id:

            ingredient["_id"] = str(ingredient["_id"])

            return jsonify(ingredient), 200

    return jsonify({"error": "Embedded ingredient not found"}), 404


# Update Dish Ingredient Function
@dishes_bp.patch("/dishes/<dish_id>/ingredients/<entry_id>")
@token_required
def update_dish_ingredient(dish_id, entry_id):

    # Validation for dish ID
    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    # Validation for embedded ingredient ID
    if not ObjectId.is_valid(entry_id):
        return jsonify({"error": "Invalid embedded ingredient ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    # Validation for dish not found
    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    existing_entry = None

    for ingredient in dish.get("ingredients", []):
        if str(ingredient.get("_id")) == entry_id:
            existing_entry = ingredient
            break

    # Validation for embedded ingredient not found
    if existing_entry is None:
        return jsonify({"error": "Embedded ingredient not found"}), 404

    data = request.get_json(silent=True)

    # Validation for update data
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "No update data provided"}), 400

    allowed_fields = [
        "ingredient_id",
        "ingredient_name",
        "quantity",
        "unit"
    ]

    for field in data:
        # Validation for allowed update fields
        if field not in allowed_fields:
            return jsonify({"error": "Invalid update field"}), 400

    # Validation for ingredient name
    if "ingredient_name" in data:
        # Validation for ingredient name
        if (
            not isinstance(data["ingredient_name"], str)
            or not data["ingredient_name"].strip()
        ):
            return jsonify({"error": "Invalid ingredient name"}), 400

    # Validation for ingredient unit
    if "unit" in data:
        # Validation for ingredient unit
        if (
            not isinstance(data["unit"], str)
            or not data["unit"].strip()
        ):
            return jsonify({"error": "Invalid ingredient unit"}), 400

    # Validation for ingredient quantity
    if "quantity" in data:
        quantity = data["quantity"]

        # Validation for ingredient quantity
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, (int, float))
            or quantity <= 0
        ):
            return jsonify({"error": "Invalid ingredient quantity"}), 400

    # Validation for ingredient ID
    if "ingredient_id" in data:
        ingredient_id = data["ingredient_id"]

        try:
            mongo_id = ObjectId(ingredient_id)
        # Validation for invalid ID
        except (InvalidId, TypeError):
            return jsonify({"error": "Invalid ingredient ID"}), 400

        existing_ingredient = ingredients_collection.find_one({
            "_id": mongo_id
        })

        # Validation for ingredient not found
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

    # Validation for record not found
    if result.matched_count == 0:
        return jsonify({"error": "Embedded ingredient not found"}), 404

    return jsonify({
        "message": "Embedded ingredient updated successfully"
    }), 200


# Delete Dish Ingredient Function
@dishes_bp.delete("/dishes/<dish_id>/ingredients/<entry_id>")
@token_required
@admin_required
def delete_dish_ingredient(dish_id, entry_id):

    # Validation for dish ID
    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    # Validation for embedded ingredient ID
    if not ObjectId.is_valid(entry_id):
        return jsonify({"error": "Invalid embedded ingredient ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    # Validation for dish not found
    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    existing_entry = None

    for ingredient in dish.get("ingredients", []):
        if str(ingredient.get("_id")) == entry_id:
            existing_entry = ingredient
            break

    # Validation for embedded ingredient not found
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

    # Validation for embedded ingredient not found
    if result.modified_count == 0:
        return jsonify({"error": "Embedded ingredient not found"}), 404

    return jsonify({
        "message": "Embedded ingredient deleted successfully"
    }), 200




# Calculate Dish Cost Function
@dishes_bp.get("/dishes/<dish_id>/cost")
@token_required
def get_dish_cost(dish_id):

    # Validation for dish ID
    if not ObjectId.is_valid(dish_id):
        return jsonify({"error": "Invalid dish ID"}), 400

    dish = dishes_collection.find_one({
        "_id": ObjectId(dish_id)
    })

    # Validation for dish not found
    if dish is None:
        return jsonify({"error": "Dish not found"}), 404

    total_cost = 0

    for ingredient in dish.get("ingredients", []):

        ingredient_id = ingredient.get("ingredient_id")

        # Validation for ingredient ID
        if not ObjectId.is_valid(ingredient_id):
            return jsonify({"error": "Invalid ingredient ID"}), 400

        main_ingredient = ingredients_collection.find_one({
            "_id": ObjectId(ingredient_id)
        })

        # Validation for ingredient not found
        if main_ingredient is None:
            return jsonify({"error": "Ingredient not found"}), 404

        # Validation for ingredient units
        if ingredient["unit"] != main_ingredient["unit"]:
            return jsonify({"error": "Ingredient units do not match"}), 400

        ingredient_cost = ingredient["quantity"] * main_ingredient["purchase_cost"]

        total_cost += ingredient_cost

    selling_price = dish["selling_price"]

    gross_profit = selling_price - total_cost

    if selling_price > 0:
        food_cost_percentage = (total_cost / selling_price) * 100
        food_cost_percentage = round(food_cost_percentage, 2)
    else:
        food_cost_percentage = None

    return jsonify({
        "selling_price": round(selling_price, 2),
        "total_ingredient_cost": round(total_cost, 2),
        "estimated_gross_profit": round(gross_profit, 2),
        "food_cost_percentage": food_cost_percentage
    }), 200


