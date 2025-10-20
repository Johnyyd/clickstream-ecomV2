from bson import ObjectId
from db import products_col
from datetime import datetime
import pytz

def slugify(name: str) -> str:
    s = name.lower()
    chars = [" ", "/", "\\", ",", ".", "(", ")", "[", "]", "{", "}", "\'", "\""]
    for ch in chars:
        s = s.replace(ch, "-")
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
    {"name": "Apple MacBook Air M3", "category": "computer", "price": 1300, "tags": ["electronics","lightweight"]},

    # ---- Phones ----
    {"name": "Google Pixel 8", "category": "phone", "price": 799, "tags": ["electronics","mobile"]},
    {"name": "Samsung Galaxy S24", "category": "phone", "price": 950, "tags": ["electronics","android"]},
    {"name": "Apple iPhone 15 Pro", "category": "phone", "price": 1199, "tags": ["electronics","mobile"]},
    {"name": "Xiaomi Mi 14", "category": "phone", "price": 700, "tags": ["electronics","budget"]},
    {"name": "Sony Xperia 5 V", "category": "phone", "price": 950, "tags": ["electronics","camera"]},

    # ---- Drinks ----
    {"name": "Coca Cola Bottle", "category": "drink", "price": 2.0, "tags": ["beverage","cold"]},
    {"name": "Green Tea", "category": "drink", "price": 2.5, "tags": ["beverage","hot"]},
    {"name": "Latte Coffee", "category": "drink", "price": 3.5, "tags": ["beverage","hot"]},
    {"name": "Orange Juice", "category": "drink", "price": 2.8, "tags": ["beverage","fruit"]},
    {"name": "Mineral Water", "category": "drink", "price": 1.0, "tags": ["beverage","cold"]},
    {"name": "Red Bull Energy", "category": "drink", "price": 2.5, "tags": ["beverage","energy"]},

    # ---- Food ----
    {"name": "Burger Beef", "category": "food", "price": 8, "tags": ["meal","fastfood"]},
    {"name": "Pasta Carbonara", "category": "food", "price": 12, "tags": ["meal","italian"]},
    {"name": "Steak Medium Rare", "category": "food", "price": 25, "tags": ["meal","western"]},
    {"name": "Chicken Curry", "category": "food", "price": 14, "tags": ["meal","asian"]},
    {"name": "Vegan Salad Bowl", "category": "food", "price": 11, "tags": ["meal","healthy"]},
    {"name": "Ramen Noodle Soup", "category": "food", "price": 10, "tags": ["meal","japanese"]},

    # ---- Glasses ----
    {"name": "Ray-Ban Aviator", "category": "glasses", "price": 150, "tags": ["fashion","outdoor"]},
    {"name": "Gucci Designer Glasses", "category": "glasses", "price": 350, "tags": ["fashion","luxury"]},
    {"name": "Blue Light Glasses", "category": "glasses", "price": 70, "tags": ["vision","work"]},
    {"name": "Kids Reading Glasses", "category": "glasses", "price": 30, "tags": ["vision","kids"]},
    {"name": "Oakley Sport Glasses", "category": "glasses", "price": 120, "tags": ["fashion","outdoor"]},

    # ---- Pants ----
    {"name": "Cargo Pants Green", "category": "pants", "price": 50, "tags": ["clothing","casual"]},
    {"name": "Slim Fit Jeans", "category": "pants", "price": 55, "tags": ["clothing","casual"]},
    {"name": "Formal Suit Pants", "category": "pants", "price": 95, "tags": ["clothing","formal"]},
    {"name": "Yoga Leggings", "category": "pants", "price": 45, "tags": ["clothing","sport"]},

    # ---- Shoes ----
    {"name": "Adidas Ultraboost", "category": "shoes", "price": 160, "tags": ["clothing","sport"]},
    {"name": "Nike Air Jordan 1", "category": "shoes", "price": 190, "tags": ["clothing","fashion"]},
    {"name": "Converse Chuck Taylor", "category": "shoes", "price": 70, "tags": ["clothing","casual"]},
    {"name": "Timberland Boots", "category": "shoes", "price": 200, "tags": ["clothing","outdoor"]},

    # ---- Shirts ----
    {"name": "Polo Shirt Blue", "category": "shirt", "price": 25, "tags": ["clothing","casual"]},
    {"name": "Hoodie Black", "category": "shirt", "price": 45, "tags": ["clothing","casual"]},
    {"name": "Silk Shirt", "category": "shirt", "price": 70, "tags": ["clothing","luxury"]},
    {"name": "Winter Coat", "category": "shirt", "price": 120, "tags": ["clothing","outerwear"]},

    # ---- Toys ----
    {"name": "LEGO Star Wars Set", "category": "toy", "price": 150, "tags": ["kids","creative"]},
    {"name": "Barbie Dreamhouse", "category": "toy", "price": 200, "tags": ["kids","doll"]},
    {"name": "Hot Wheels Track", "category": "toy", "price": 60, "tags": ["kids","cars"]},
    {"name": "Rubik’s Cube", "category": "toy", "price": 10, "tags": ["puzzle","classic"]},
    {"name": "Remote Control Car", "category": "toy", "price": 40, "tags": ["kids","gadget"]},

    # ---- Kitchen ----
    {"name": "Philips Air Fryer", "category": "kitchen", "price": 130, "tags": ["appliance","cooking"]},
    {"name": "Tefal Non-stick Pan", "category": "kitchen", "price": 35, "tags": ["cookware","daily"]},
    {"name": "Sharp Microwave Oven", "category": "kitchen", "price": 120, "tags": ["appliance","heating"]},
    {"name": "Bosch Dishwasher", "category": "kitchen", "price": 650, "tags": ["appliance","cleaning"]},
    {"name": "Kitchen Knife Set", "category": "kitchen", "price": 50, "tags": ["cookware","sharp"]},

    # ---- Books ----
    {"name": "Atomic Habits", "category": "book", "price": 18, "tags": ["selfhelp","bestseller"]},
    {"name": "The Pragmatic Programmer", "category": "book", "price": 35, "tags": ["tech","education"]},
    {"name": "The Hobbit", "category": "book", "price": 25, "tags": ["fantasy","classic"]},
    {"name": "Clean Code", "category": "book", "price": 40, "tags": ["tech","programming"]},
    {"name": "Ikigai", "category": "book", "price": 15, "tags": ["selfhelp","lifestyle"]},

    # ---- Furniture ----
    {"name": "IKEA Office Chair", "category": "furniture", "price": 180, "tags": ["home","office"]},
    {"name": "Wooden Dining Table", "category": "furniture", "price": 400, "tags": ["home","interior"]},
    {"name": "Sofa 3-Seater", "category": "furniture", "price": 750, "tags": ["home","livingroom"]},
    {"name": "Queen Size Bed Frame", "category": "furniture", "price": 600, "tags": ["home","bedroom"]},
    {"name": "Bookshelf 5-Tier", "category": "furniture", "price": 120, "tags": ["home","storage"]},

    # ---- Beauty ----
    {"name": "L'Oreal Moisturizer", "category": "beauty", "price": 25, "tags": ["skincare","daily"]},
    {"name": "Dior Perfume Sauvage", "category": "beauty", "price": 120, "tags": ["fragrance","luxury"]},
    {"name": "Maybelline Mascara", "category": "beauty", "price": 15, "tags": ["makeup","daily"]},
    {"name": "Nivea Lip Balm", "category": "beauty", "price": 5, "tags": ["skincare","budget"]},

    # ---- Accessories ----
    {"name": "Apple Watch Series 9", "category": "accessory", "price": 399, "tags": ["wearable","electronics"]},
    {"name": "Samsung Galaxy Buds 3", "category": "accessory", "price": 150, "tags": ["audio","wireless"]},
    {"name": "Fossil Leather Wallet", "category": "accessory", "price": 60, "tags": ["fashion","men"]},
    {"name": "Silver Chain Necklace", "category": "accessory", "price": 90, "tags": ["fashion","jewelry"]},

    # ---- Sports ----
    {"name": "Wilson Tennis Racket", "category": "sport", "price": 120, "tags": ["tennis","outdoor"]},
    {"name": "Spalding Basketball", "category": "sport", "price": 40, "tags": ["basketball","indoor"]},
    {"name": "Nike Gym Bag", "category": "sport", "price": 60, "tags": ["fitness","travel"]},
    {"name": "Adidas Soccer Ball", "category": "sport", "price": 35, "tags": ["soccer","outdoor"]},
    {"name": "Yoga Mat Pro", "category": "sport", "price": 50, "tags": ["fitness","indoor"]},
    
    # ---- Pet ----
    {"name": "Purina One Dog Food 5kg", "category": "pet", "price": 25, "tags": ["pet","dog","food"]},
    {"name": "Whiskas Cat Food 3kg", "category": "pet", "price": 20, "tags": ["pet","cat","food"]},
    {"name": "Cat Scratching Post", "category": "pet", "price": 45, "tags": ["pet","toy"]},
    {"name": "Pet Grooming Kit", "category": "pet", "price": 35, "tags": ["pet","care"]},
    {"name": "Automatic Pet Feeder", "category": "pet", "price": 80, "tags": ["pet","smart"]},
    {"name": "Dog Leash Nylon", "category": "pet", "price": 15, "tags": ["pet","accessory"]},
    {"name": "Fish Tank 40L", "category": "pet", "price": 70, "tags": ["pet","aquarium"]},
    {"name": "Bird Cage Medium", "category": "pet", "price": 55, "tags": ["pet","bird"]},

    # ---- Garden ----
    {"name": "Garden Hose 20m", "category": "garden", "price": 25, "tags": ["outdoor","watering"]},
    {"name": "Fertilizer Organic Mix", "category": "garden", "price": 18, "tags": ["plants","growth"]},
    {"name": "Ceramic Plant Pot", "category": "garden", "price": 12, "tags": ["decor","indoor"]},
    {"name": "Pruning Shears", "category": "garden", "price": 20, "tags": ["tools","plants"]},
    {"name": "LED Grow Light", "category": "garden", "price": 60, "tags": ["plants","tech"]},
    {"name": "Compost Bin 30L", "category": "garden", "price": 45, "tags": ["eco","outdoor"]},
    {"name": "Garden Gloves Pair", "category": "garden", "price": 8, "tags": ["tools","safety"]},
    {"name": "Watering Can Metal", "category": "garden", "price": 15, "tags": ["tools","watering"]},

    # ---- Health ----
    {"name": "Omron Blood Pressure Monitor", "category": "health", "price": 60, "tags": ["medical","device"]},
    {"name": "3M N95 Mask Pack", "category": "health", "price": 25, "tags": ["safety","protection"]},
    {"name": "Digital Thermometer", "category": "health", "price": 10, "tags": ["medical","device"]},
    {"name": "Vitamin C 1000mg", "category": "health", "price": 18, "tags": ["supplement","immune"]},
    {"name": "First Aid Kit Box", "category": "health", "price": 30, "tags": ["safety","medical"]},
    {"name": "Whey Protein Powder", "category": "health", "price": 55, "tags": ["fitness","nutrition"]},
    {"name": "Yoga Foam Roller", "category": "health", "price": 25, "tags": ["fitness","recovery"]},
    {"name": "Infrared Thermometer", "category": "health", "price": 45, "tags": ["medical","infrared"]},

    # ---- Automotive ----
    {"name": "Car Vacuum Cleaner", "category": "automotive", "price": 40, "tags": ["car","cleaning"]},
    {"name": "Michelin Tire 17-inch", "category": "automotive", "price": 120, "tags": ["car","parts"]},
    {"name": "Castrol Engine Oil 4L", "category": "automotive", "price": 45, "tags": ["car","maintenance"]},
    {"name": "Car Phone Holder", "category": "automotive", "price": 20, "tags": ["car","accessory"]},
    {"name": "LED Headlight Bulb Set", "category": "automotive", "price": 60, "tags": ["car","lighting"]},
    {"name": "Portable Tire Inflator", "category": "automotive", "price": 55, "tags": ["car","emergency"]},
    {"name": "Dashboard Camera 1080p", "category": "automotive", "price": 95, "tags": ["car","security"]},
    {"name": "Car Air Freshener", "category": "automotive", "price": 10, "tags": ["car","fragrance"]},

]

    
    col = products_col()
    for p in more_products:
        p["_id"] = ObjectId()
        p["slug"] = slugify(p["name"])
        p["image_url"] = f"/static/images/{p['slug']}.jpg"
    col.insert_many(more_products)
    print(f"Inserted {len(more_products)} products")

if __name__ == "__main__":
    seed_more_products()
