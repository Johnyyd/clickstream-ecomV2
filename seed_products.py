from bson import ObjectId
from db import get_db
from datetime import datetime
import pytz

def slugify(name: str) -> str:
    s = name.lower()
    # characters to normalize to dashes
    chars = [" ", "/", "\\", ",", ".", "(", ")", "[", "]", "{", "}", "\'", "\""]
    for ch in chars:
        s = s.replace(ch, "-")
    # collapse multiple dashes
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")
def seed_more_products():
    more_products = [
        # ---- Computers ----
        {"name": "Lenovo ThinkPad X1", "category": "computer", "price": 1500, "tags": ["electronics","laptop"]},
        {"name": "Asus ROG Strix", "category": "computer", "price": 1800, "tags": ["electronics","gaming","laptop"]},
        {"name": "HP Spectre x360", "category": "computer", "price": 1400, "tags": ["electronics","laptop"]},
        {"name": "Microsoft Surface Laptop 5", "category": "computer", "price": 1600, "tags": ["electronics","portable"]},
        {"name": "Acer Aspire 7", "category": "computer", "price": 900, "tags": ["electronics","budget"]},
        {"name": "Alienware M16", "category": "computer", "price": 2200, "tags": ["electronics","gaming"]},
        
        # ---- Phones ----
        {"name": "Google Pixel 8", "category": "phone", "price": 799, "tags": ["electronics","mobile"]},
        {"name": "OnePlus 11", "category": "phone", "price": 699, "tags": ["electronics","mobile"]},
        {"name": "Xiaomi Mi 13", "category": "phone", "price": 650, "tags": ["electronics","mobile"]},
        {"name": "Oppo Find X6", "category": "phone", "price": 720, "tags": ["electronics","mobile"]},
        {"name": "Sony Xperia 5 V", "category": "phone", "price": 950, "tags": ["electronics","camera"]},
        {"name": "Nokia G60", "category": "phone", "price": 400, "tags": ["electronics","budget"]},
        
        # ---- Drinks ----
        {"name": "Coca Cola Bottle", "category": "drink", "price": 2.0, "tags": ["beverage","cold"]},
        {"name": "Green Tea", "category": "drink", "price": 2.5, "tags": ["beverage","hot"]},
        {"name": "Latte Coffee", "category": "drink", "price": 3.5, "tags": ["beverage","hot"]},
        {"name": "Orange Juice", "category": "drink", "price": 2.8, "tags": ["beverage","fruit"]},
        {"name": "Mineral Water", "category": "drink", "price": 1.0, "tags": ["beverage","cold"]},
        {"name": "Energy Drink Monster", "category": "drink", "price": 2.2, "tags": ["beverage","energy"]},
        
        # ---- Food ----
        {"name": "Burger Beef", "category": "food", "price": 8, "tags": ["meal","fastfood"]},
        {"name": "Pasta Carbonara", "category": "food", "price": 12, "tags": ["meal","italian"]},
        {"name": "Steak Medium Rare", "category": "food", "price": 25, "tags": ["meal","western"]},
        {"name": "Chicken Curry", "category": "food", "price": 14, "tags": ["meal","asian"]},
        {"name": "Fried Rice", "category": "food", "price": 9, "tags": ["meal","asian"]},
        {"name": "Salmon Sushi Roll", "category": "food", "price": 18, "tags": ["meal","japanese"]},
        {"name": "Vegan Salad Bowl", "category": "food", "price": 11, "tags": ["meal","healthy"]},
        
        # ---- Glasses ----
        {"name": "Oakley Sport Glasses", "category": "glasses", "price": 120, "tags": ["fashion","sport"]},
        {"name": "Gucci Designer Glasses", "category": "glasses", "price": 350, "tags": ["fashion","luxury"]},
        {"name": "Blue Light Blocking Glasses", "category": "glasses", "price": 80, "tags": ["vision","work"]},
        {"name": "Kids Reading Glasses", "category": "glasses", "price": 30, "tags": ["vision","kids"]},
        
        # ---- Pants ----
        {"name": "Cargo Pants Green", "category": "pants", "price": 50, "tags": ["clothing","casual"]},
        {"name": "Jogger Pants Black", "category": "pants", "price": 45, "tags": ["clothing","sport"]},
        {"name": "Slim Fit Jeans", "category": "pants", "price": 55, "tags": ["clothing","casual"]},
        {"name": "Khaki Pants Beige", "category": "pants", "price": 65, "tags": ["clothing","formal"]},
        
        # ---- Shoes ----
        {"name": "Adidas Ultraboost", "category": "shoes", "price": 160, "tags": ["clothing","sport"]},
        {"name": "Converse Chuck Taylor", "category": "shoes", "price": 70, "tags": ["clothing","casual"]},
        {"name": "Puma Running Shoes", "category": "shoes", "price": 95, "tags": ["clothing","sport"]},
        {"name": "Reebok Classic", "category": "shoes", "price": 85, "tags": ["clothing","casual"]},
        {"name": "Timberland Boots", "category": "shoes", "price": 200, "tags": ["clothing","outdoor"]},
        
        # ---- Shirts ----
        {"name": "Polo Shirt Blue", "category": "shirt", "price": 25, "tags": ["clothing","casual"]},
        {"name": "Hoodie Black", "category": "shirt", "price": 45, "tags": ["clothing","casual"]},
        {"name": "Sweater Grey", "category": "shirt", "price": 40, "tags": ["clothing","casual"]},
        {"name": "Flannel Shirt Red", "category": "shirt", "price": 30, "tags": ["clothing","casual"]},
        {"name": "Silk Shirt", "category": "shirt", "price": 70, "tags": ["clothing","luxury"]},
        {"name": "Denim Jacket", "category": "shirt", "price": 80, "tags": ["clothing","casual"]},
        {"name": "Winter Coat", "category": "shirt", "price": 120, "tags": ["clothing","outerwear"]},
        {"name": "Trench Coat", "category": "shirt", "price": 150, "tags": ["clothing","formal"]},
    ]
    
    db = get_db()
    for p in more_products:
        p["_id"] = ObjectId()
        p["created_at"] = datetime.now(pytz.UTC)
        # Ensure image_url is present and points to static images
        slug = slugify(p["name"]) if p.get("name") else str(p["_id"])
        p["slug"] = slug
        # default to .jpg; users can drop images into static/images with matching names
        p["image_url"] = f"/static/images/{slug}.jpg"
    db.products.insert_many(more_products)
    print("Inserted more products:", len(more_products))

if __name__ == "__main__":
    seed_more_products()
