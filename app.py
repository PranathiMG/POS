from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, static_folder=".", template_folder="templates")
@app.route("/healthz")
def health_check():
    return jsonify({"status": "ok"}), 200

from flask import send_from_directory

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml')
    
# Serve index.html
@app.route("/")
def index():
    return render_template("index.html")

# -------------------------------
# Chatbot API
# -------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").lower()
    inventory = data.get("inventory", [])
    sales = data.get("sales", [])
    revenue = data.get("revenue", 0)
    profit = data.get("profit", 0)

    # --- Stock request ---
    if "stock" in user_message or "products" in user_message:
        if inventory:
            reply = "Available products:\n" + "\n".join(
                [f"{p['name']} - Qty: {p['stock']}" for p in inventory]
            )
        else:
            reply = "No products available in stock."
        return jsonify({"reply": reply})

    # --- Low stock request ---
    elif "low stock" in user_message or "reorder" in user_message:
        low_items = [i for i in inventory if i['stock'] < 5]
        if low_items:
            reply = "⚠️ Low stock items:\n" + "\n".join(
                [f"{i['name']} - Qty: {i['stock']}" for i in low_items]
            )
        else:
            reply = "No low stock items. All good!"
        return jsonify({"reply": reply})

    # --- Sales history ---
    elif "history" in user_message or "sales" in user_message:
        if sales:
            reply = "Sales history:\n" + "\n".join(
                [f"{s['items']} sold: ₹{s['total']} on {s['date']}" for s in sales]
            )
        else:
            reply = "No sales history found."
        return jsonify({"reply": reply})

    # --- Revenue / Profit ---
    elif "revenue" in user_message or "profit" in user_message:
        reply = f"Total Revenue: ₹{revenue:.2f}\nTotal Profit: ₹{profit:.2f}"
        return jsonify({"reply": reply})

    # --- Basic greetings ---
    elif any(greet in user_message for greet in ["hi", "hello", "hey"]):
        reply = "Hello! 👋 How can I assist you today?"
    elif any(greet in user_message for greet in ["how are you", "how ru", "how r u"]):
        reply = "I'm doing great! How about you?"
    elif "how is your day" in user_message or "how's your day" in user_message:
        reply = "My day is full of helping you manage your store! 😊"
    elif any(greet in user_message for greet in ["Good morning", "good mrng", "Gm", "gm"]):
        reply = "Very Good morning 😊"
    elif any(greet in user_message for greet in ["Good evening", "good evening", "good evng"]):
        reply = "Very Good evening😊"
    else:
        reply = "I can show stock, low stock, sales history, revenue, or answer simple greetings. Try asking about stock, low stock, or sales."

    return jsonify({"reply": reply})

# -------------------------------
# API endpoints for inventory and sales (unchanged)
# -------------------------------
@app.route("/api/products", methods=["GET"])
def get_products():
    products = supabase.table("products").select("*").execute()
    return jsonify(products.data)

@app.route("/api/history", methods=["GET"])
def get_history():
    history = supabase.table("sales_history").select("*").order("created_at", desc=True).execute()
    return jsonify(history.data)

@app.route("/api/add_product", methods=["POST"])
def add_product():
    data = request.json
    name = data.get("name")
    quantity = data.get("quantity", 0)
    if not name:
        return jsonify({"error": "Product name is required"}), 400
    supabase.table("products").insert({"name": name, "quantity": quantity}).execute()
    return jsonify({"message": f"Product '{name}' added successfully."})

@app.route("/api/add_sale", methods=["POST"])
def add_sale():
    data = request.json
    product_name = data.get("product_name")
    quantity = data.get("quantity", 0)
    if not product_name:
        return jsonify({"error": "Product name is required"}), 400

    # Check product exists
    product = supabase.table("products").select("*").eq("name", product_name).execute()
    if not product.data:
        return jsonify({"error": "Product not found"}), 404

    current_qty = product.data[0]['quantity']
    new_qty = current_qty - quantity
    if new_qty < 0:
        return jsonify({"error": "Not enough stock"}), 400

    # Update stock
    supabase.table("products").update({"quantity": new_qty}).eq("name", product_name).execute()

    # Add sale record
    supabase.table("sales_history").insert({"product_name": product_name, "quantity": quantity}).execute()
    return jsonify({"message": f"Sale recorded for '{product_name}', quantity: {quantity}."})
#-----LOW STOCK

# -------------------------------
# Low Stock API
# -------------------------------
@app.route("/api/low_stock", methods=["GET"])
def get_low_stock():
    """
    Fetch all products with quantity < 5
    """
    response = supabase.table("products").select("*").lt("quantity", 5).execute()
    if response.error:
        return jsonify({"error": str(response.error)}), 400
    if not response.data:
        return jsonify({"message": "No low stock items. All products have sufficient stock."})
    return jsonify({"low_stock_items": response.data})
# -------------------------------
# Run Flask
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
