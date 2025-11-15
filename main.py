import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from database import db, create_document, get_documents
from schemas import Product, Category, Cart, CartItem, Order, OrderItem, Customer

app = FastAPI(title="Department Store E‑commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Department Store API is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or "unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Seed minimal data if empty
@app.post("/seed")
def seed():
    try:
        if db["category"].count_documents({}) == 0:
            categories = [
                {"name": "Electronics", "slug": "electronics", "image": "https://images.unsplash.com/photo-1518779578993-ec3579fee39f"},
                {"name": "Home & Kitchen", "slug": "home-kitchen", "image": "https://images.unsplash.com/photo-1495546968767-f0573cca821e"},
                {"name": "Beauty", "slug": "beauty", "image": "https://images.unsplash.com/photo-1512496015851-a90fb38ba796"},
                {"name": "Clothing", "slug": "clothing", "image": "https://images.unsplash.com/photo-1520975916090-3105956dac38"}
            ]
            for c in categories:
                create_document("category", c)
        if db["product"].count_documents({}) == 0:
            sample = [
                {
                    "title": "Wireless Headphones",
                    "description": "Noise-cancelling over-ear headphones",
                    "price": 129.99,
                    "compare_at_price": 179.99,
                    "category_slug": "electronics",
                    "brand": "SoundMax",
                    "sku": "HD-1001",
                    "images": ["https://images.unsplash.com/photo-1512314889357-e157c22f938d"],
                    "rating": 4.6,
                    "stock": 25,
                    "attributes": {"color": "black"}
                },
                {
                    "title": "Stainless Cookware Set",
                    "description": "10-piece pots and pans set",
                    "price": 89.0,
                    "category_slug": "home-kitchen",
                    "brand": "ChefPro",
                    "sku": "CK-2002",
                    "images": ["https://images.unsplash.com/photo-1514517220039-39c7b53c0b18"],
                    "rating": 4.4,
                    "stock": 40,
                    "attributes": {"pieces": "10"}
                },
                {
                    "title": "Organic Face Serum",
                    "description": "Vitamin C brightening serum",
                    "price": 24.5,
                    "category_slug": "beauty",
                    "brand": "GlowLab",
                    "sku": "GL-3003",
                    "images": ["https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd"],
                    "rating": 4.7,
                    "stock": 60,
                    "attributes": {"size": "30ml"}
                }
            ]
            for p in sample:
                create_document("product", p)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Catalog endpoints
@app.get("/categories")
def list_categories():
    try:
        cats = get_documents("category", {})
        for c in cats:
            c["_id"] = str(c["_id"])  # make JSON serializable
        return cats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    try:
        filter_q = {}
        if category:
            filter_q["category_slug"] = category
        products = get_documents("product", filter_q)
        # simple search filter if q
        if q:
            q_lower = q.lower()
            products = [p for p in products if q_lower in p.get("title", "").lower() or q_lower in p.get("description", "").lower()]
        for p in products:
            p["_id"] = str(p["_id"])  # serialize
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/{product_id}")
def get_product(product_id: str):
    from bson import ObjectId
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        doc["_id"] = str(doc["_id"])  # serialize
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cart endpoints (session-based simple cart)
@app.post("/cart")
def create_or_update_cart(cart: Cart):
    try:
        # Recalculate subtotal and timestamp
        subtotal = sum(item.price * item.quantity for item in cart.items)
        data = cart.model_dump()
        data["subtotal"] = round(subtotal, 2)
        data["updated_at"] = datetime.now(timezone.utc)

        existing = db["cart"].find_one({"session_id": cart.session_id})
        if existing:
            db["cart"].update_one({"_id": existing["_id"]}, {"$set": data})
        else:
            create_document("cart", data)
        return {"status": "ok", "subtotal": data["subtotal"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cart/{session_id}")
def get_cart(session_id: str):
    try:
        cart = db["cart"].find_one({"session_id": session_id})
        if not cart:
            return {"session_id": session_id, "items": [], "subtotal": 0.0}
        cart["_id"] = str(cart["_id"])  # serialize
        return cart
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Checkout / Order
class CheckoutPayload(BaseModel):
    session_id: str
    customer: Customer


@app.post("/checkout")
def checkout(payload: CheckoutPayload):
    try:
        cart = db["cart"].find_one({"session_id": payload.session_id})
        if not cart or not cart.get("items"):
            raise HTTPException(status_code=400, detail="Cart is empty")
        items = [
            OrderItem(
                product_id=i["product_id"],
                title=i["title"],
                price=float(i["price"]),
                quantity=int(i["quantity"]),
                image=i.get("image")
            ) for i in cart["items"]
        ]
        subtotal = float(cart.get("subtotal", 0.0))
        tax = round(subtotal * 0.08, 2)
        total = round(subtotal + tax, 2)
        order = Order(
            session_id=payload.session_id,
            customer=payload.customer,
            items=items,
            subtotal=subtotal,
            tax=tax,
            total=total,
            placed_at=datetime.now(timezone.utc)
        )
        order_id = create_document("order", order)
        # clear cart
        db["cart"].delete_one({"session_id": payload.session_id})
        return {"status": "ok", "order_id": order_id, "total": total}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
