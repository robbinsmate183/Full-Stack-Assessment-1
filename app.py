from flask import Flask, jsonify
from routes.ingredients import ingredients_bp
from routes.recipes import dishes_bp

app = Flask(__name__)

app.register_blueprint(ingredients_bp)
app.register_blueprint(dishes_bp)

@app.get("/")
def home():
    return jsonify({"message": "Restaurant API is running"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5001)