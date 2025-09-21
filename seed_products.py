from datetime import datetime
from bson import ObjectId
from db import get_db

def seed_products():
    products = [
        {"name": "Laptop Dell XPS 13", "category": "computer", "price": 1200, "tags": ["electronics","laptop"]},
        {"name": "MacBook Pro 14", "category": "computer", "price": 2000, "tags": ["electronics","laptop"]},
        {"name": "iPhone 15", "category": "phone", "price": 999, "tags": ["electronics","mobile"]},
        {"name": "Samsung Galaxy S23", "category": "phone", "price": 899, "tags": ["electronics","mobile"]},
        {"name": "Pepsi Can", "category": "drink", "price": 1.5, "tags": ["beverage","cold"]},
        {"name": "Espresso Coffee", "category": "drink", "price": 3.0, "tags": ["beverage","hot"]},
        {"name": "Pizza Margherita", "category": "food", "price": 10, "tags": ["meal","fastfood"]},
        {"name": "Sushi Set", "category": "food", "price": 15, "tags": ["meal","japanese"]},
        {"name": "RayBan Sunglasses", "category": "glasses", "price": 150, "tags": ["fashion","accessory"]},
        {"name": "Reading Glasses", "category": "glasses", "price": 50, "tags": ["vision","accessory"]},
        {"name": "Blue Jeans", "category": "pants", "price": 40, "tags": ["clothing","casual"]},
        {"name": "Formal Trousers", "category": "pants", "price": 60, "tags": ["clothing","formal"]},
        {"name": "Nike Air Shoes", "category": "shoes", "price": 120, "tags": ["clothing","sport"]},
        {"name": "Leather Boots", "category": "shoes", "price": 180, "tags": ["clothing","casual"]},
        {"name": "T-Shirt White", "category": "shirt", "price": 20, "tags": ["clothing","casual"]},
        {"name": "Formal Shirt", "category": "shirt", "price": 35, "tags": ["clothing","formal"]},
    ]
    db = get_db()
    for p in products:
        p["_id"] = ObjectId()
        p["created_at"] = datetime.utcnow()
    db.products.insert_many(products)
    print("Seeded products:", len(products))

if __name__ == "__main__":
    seed_products()
