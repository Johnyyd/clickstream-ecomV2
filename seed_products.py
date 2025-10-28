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



    # ---- Computers (mở rộng) ----
        {"name": "Dell XPS 13", "category": "computer", "price": 1350, "tags": ["electronics", "laptop", "premium"]},
        {"name": "Razer Blade 15", "category": "computer", "price": 2200, "tags": ["electronics", "gaming", "laptop"]},
        {"name": "LG Gram 17", "category": "computer", "price": 1700, "tags": ["electronics", "lightweight", "large-screen"]},
        {"name": "MSI GF63 Thin", "category": "computer", "price": 850, "tags": ["electronics", "gaming", "budget"]},
        {"name": "Framework Laptop", "category": "computer", "price": 1100, "tags": ["electronics", "modular", "repairable"]},

        # ---- Phones (mở rộng) ----
        {"name": "OnePlus 12", "category": "phone", "price": 899, "tags": ["electronics", "android", "flagship"]},
        {"name": "Nothing Phone (2)", "category": "phone", "price": 699, "tags": ["electronics", "unique", "design"]},
        {"name": "Motorola Edge 50", "category": "phone", "price": 550, "tags": ["electronics", "midrange"]},
        {"name": "Oppo Find X7", "category": "phone", "price": 950, "tags": ["electronics", "camera", "premium"]},
        {"name": "Realme GT 6", "category": "phone", "price": 480, "tags": ["electronics", "performance", "budget"]},

        # ---- Drinks (mở rộng) ----
        {"name": "Pepsi Can 330ml", "category": "drink", "price": 1.5, "tags": ["beverage", "cold", "soda"]},
        {"name": "Matcha Latte", "category": "drink", "price": 4.0, "tags": ["beverage", "hot", "healthy"]},
        {"name": "Smoothie Strawberry", "category": "drink", "price": 5.5, "tags": ["beverage", "fruit", "cold"]},
        {"name": "Espresso Shot", "category": "drink", "price": 2.0, "tags": ["beverage", "hot", "coffee"]},
        {"name": "Monster Energy Zero", "category": "drink", "price": 2.8, "tags": ["beverage", "energy", "sugarfree"]},

        # ---- Food (mở rộng) ----
        {"name": "Pizza Margherita", "category": "food", "price": 15, "tags": ["meal", "italian", "fastfood"]},
        {"name": "Sushi Platter 12pcs", "category": "food", "price": 22, "tags": ["meal", "japanese", "seafood"]},
        {"name": "Grilled Salmon", "category": "food", "price": 28, "tags": ["meal", "western", "healthy"]},
        {"name": "Pad Thai Shrimp", "category": "food", "price": 13, "tags": ["meal", "thai", "noodles"]},
        {"name": "Falafel Wrap", "category": "food", "price": 9, "tags": ["meal", "vegetarian", "middle-eastern"]},

        # ---- Glasses (mở rộng) ----
        {"name": "Warby Parker Frames", "category": "glasses", "price": 95, "tags": ["vision", "fashion", "affordable"]},
        {"name": "Polarized Sunglasses", "category": "glasses", "price": 80, "tags": ["fashion", "outdoor", "uv-protection"]},
        {"name": "Prada Cat Eye", "category": "glasses", "price": 420, "tags": ["fashion", "luxury", "women"]},
        {"name": "Clip-on Sunglasses", "category": "glasses", "price": 40, "tags": ["vision", "accessory"]},

        # ---- Pants (mở rộng) ----
        {"name": "Chino Pants Beige", "category": "pants", "price": 60, "tags": ["clothing", "casual", "smart"]},
        {"name": "Jogger Sweatpants", "category": "pants", "price": 38, "tags": ["clothing", "sport", "comfort"]},
        {"name": "Leather Pants Black", "category": "pants", "price": 180, "tags": ["clothing", "luxury", "fashion"]},
        {"name": "High Waist Jeans", "category": "pants", "price": 65, "tags": ["clothing", "women", "casual"]},

        # ---- Shoes (mở rộng) ----
        {"name": "New Balance 574", "category": "shoes", "price": 90, "tags": ["clothing", "casual", "classic"]},
        {"name": "Salomon Speedcross", "category": "shoes", "price": 140, "tags": ["clothing", "outdoor", "trail"]},
        {"name": "Vans Old Skool", "category": "shoes", "price": 75, "tags": ["clothing", "skate", "casual"]},
        {"name": "Dr. Martens 1460", "category": "shoes", "price": 170, "tags": ["clothing", "boots", "punk"]},

        # ---- Shirts (mở rộng) ----
        {"name": "Flannel Check Shirt", "category": "shirt", "price": 40, "tags": ["clothing", "casual", "autumn"]},
        {"name": "Turtleneck Sweater", "category": "shirt", "price": 55, "tags": ["clothing", "winter", "warm"]},
        {"name": "Linen Summer Shirt", "category": "shirt", "price": 35, "tags": ["clothing", "casual", "breathable"]},
        {"name": "Denim Jacket", "category": "shirt", "price": 85, "tags": ["clothing", "outerwear", "casual"]},

        # ---- Toys (mở rộng) ----
        {"name": "Nerf Elite Blaster", "category": "toy", "price": 35, "tags": ["kids", "action", "outdoor"]},
        {"name": "Play-Doh 10-Pack", "category": "toy", "price": 12, "tags": ["kids", "creative", "messy"]},
        {"name": "Puzzle 1000 Pieces", "category": "toy", "price": 20, "tags": ["puzzle", "family"]},
        {"name": "Drone Mini Quad", "category": "toy", "price": 80, "tags": ["kids", "gadget", "tech"]},

        # ---- Kitchen (mở rộng) ----
        {"name": "Instant Pot Duo", "category": "kitchen", "price": 100, "tags": ["appliance", "multicooker"]},
        {"name": "Blender 1000W", "category": "kitchen", "price": 75, "tags": ["appliance", "smoothie"]},
        {"name": "Cast Iron Skillet", "category": "kitchen", "price": 45, "tags": ["cookware", "durable"]},
        {"name": "Electric Kettle 1.7L", "category": "kitchen", "price": 30, "tags": ["appliance", "daily"]},

        # ---- Books (mở rộng) ----
        {"name": "Sapiens", "category": "book", "price": 22, "tags": ["history", "bestseller"]},
        {"name": "Dune", "category": "book", "price": 18, "tags": ["scifi", "classic"]},
        {"name": "Python Crash Course", "category": "book", "price": 32, "tags": ["tech", "programming", "beginner"]},
        {"name": "The Alchemist", "category": "book", "price": 16, "tags": ["fiction", "inspiration"]},

        # ---- Furniture (mở rộng) ----
        {"name": "Standing Desk Electric", "category": "furniture", "price": 450, "tags": ["home", "office", "ergonomic"]},
        {"name": "Velvet Armchair", "category": "furniture", "price": 280, "tags": ["home", "livingroom", "comfort"]},
        {"name": "Coffee Table Glass", "category": "furniture", "price": 150, "tags": ["home", "modern"]},
        {"name": "Wardrobe 3-Door", "category": "furniture", "price": 520, "tags": ["home", "bedroom", "storage"]},

        # ---- Beauty (mở rộng) ----
        {"name": "The Ordinary Serum", "category": "beauty", "price": 12, "tags": ["skincare", "affordable"]},
        {"name": "Chanel No.5", "category": "beauty", "price": 140, "tags": ["fragrance", "luxury", "classic"]},
        {"name": "Fenty Lip Gloss", "category": "beauty", "price": 24, "tags": ["makeup", "inclusive"]},
        {"name": "Hair Dryer Ionic", "category": "beauty", "price": 65, "tags": ["haircare", "tool"]},

        # ---- Accessories (mở rộng) ----
        {"name": "Fitbit Charge 6", "category": "accessory", "price": 160, "tags": ["wearable", "fitness"]},
        {"name": "JBL Clip Speaker", "category": "accessory", "price": 50, "tags": ["audio", "portable"]},
        {"name": "Ray-Ban Wayfarer", "category": "accessory", "price": 155, "tags": ["fashion", "sunglasses"]},
        {"name": "Leather Belt Brown", "category": "accessory", "price": 45, "tags": ["fashion", "men"]},

        # ---- Sports (mở rộng) ----
        {"name": "Dumbbell Set 20kg", "category": "sport", "price": 90, "tags": ["fitness", "homegym"]},
        {"name": "Badminton Racket Pair", "category": "sport", "price": 70, "tags": ["outdoor", "racket"]},
        {"name": "Swimming Goggles", "category": "sport", "price": 25, "tags": ["swimming", "indoor"]},
        {"name": "Jump Rope Digital", "category": "sport", "price": 18, "tags": ["fitness", "cardio"]},

        # ---- Pet (mở rộng) ----
        {"name": "Aquarium Filter", "category": "pet", "price": 40, "tags": ["pet", "aquarium", "maintenance"]},
        {"name": "Hamster Wheel Silent", "category": "pet", "price": 15, "tags": ["pet", "small-animal"]},
        {"name": "Pet Bed Medium", "category": "pet", "price": 55, "tags": ["pet", "comfort"]},
        {"name": "Litter Box Auto", "category": "pet", "price": 120, "tags": ["pet", "cat", "smart"]},

        # ---- Garden (mở rộng) ----
        {"name": "Solar Garden Lights", "category": "garden", "price": 35, "tags": ["outdoor", "lighting", "eco"]},
        {"name": "Lawn Mower Electric", "category": "garden", "price": 180, "tags": ["tools", "lawncare"]},
        {"name": "Seed Starter Kit", "category": "garden", "price": 22, "tags": ["plants", "beginner"]},
        {"name": "Bird Feeder Hanging", "category": "garden", "price": 28, "tags": ["outdoor", "wildlife"]},

        # ---- Health (mở rộng) ----
        {"name": "Pulse Oximeter", "category": "health", "price": 35, "tags": ["medical", "device"]},
        {"name": "Massage Gun", "category": "health", "price": 110, "tags": ["fitness", "recovery"]},
        {"name": "Glucosamine Supplement", "category": "health", "price": 28, "tags": ["supplement", "joints"]},
        {"name": "Hand Sanitizer 500ml", "category": "health", "price": 8, "tags": ["safety", "hygiene"]},

        # ---- Automotive (mở rộng) ----
        {"name": "Jump Starter 10000mAh", "category": "automotive", "price": 85, "tags": ["car", "emergency"]},
        {"name": "Windshield Sun Shade", "category": "automotive", "price": 22, "tags": ["car", "protection"]},
        {"name": "OBD2 Scanner", "category": "automotive", "price": 50, "tags": ["car", "diagnostic"]},
        {"name": "Steering Wheel Cover", "category": "automotive", "price": 18, "tags": ["car", "comfort"]},

        # ---- DANH MỤC MỚI: Electronics (TV, Audio, etc.) ----
        {"name": "Samsung 55-inch QLED", "category": "electronics", "price": 950, "tags": ["tv", "4k", "smart"]},
        {"name": "Sony WH-1000XM5", "category": "electronics", "price": 350, "tags": ["audio", "headphones", "noise-cancelling"]},
        {"name": "Bose Soundbar 700", "category": "electronics", "price": 780, "tags": ["audio", "home-theater"]},
        {"name": "Kindle Paperwhite", "category": "electronics", "price": 140, "tags": ["ereader", "reading"]},

        # ---- DANH MỤC MỚI: Baby ----
        {"name": "Baby Stroller 3-in-1", "category": "baby", "price": 320, "tags": ["infant", "travel"]},
        {"name": "Diaper Bag Backpack", "category": "baby", "price": 65, "tags": ["parenting", "accessory"]},
        {"name": "Baby Monitor WiFi", "category": "baby", "price": 130, "tags": ["safety", "smart"]},
        {"name": "High Chair Wood", "category": "baby", "price": 110, "tags": ["furniture", "feeding"]},

        # ---- DANH MỤC MỚI: Tools ----
        {"name": "Cordless Drill 20V", "category": "tools", "price": 95, "tags": ["diy", "powertool"]},
        {"name": "Toolbox 100pcs", "category": "tools", "price": 85, "tags": ["diy", "home-repair"]},
        {"name": "Laser Level", "category": "tools", "price": 60, "tags": ["diy", "precision"]},
        {"name": "Multimeter Digital", "category": "tools", "price": 40, "tags": ["electronics", "testing"]},

        # ---- DANH MỤC MỚI: Office ----
        {"name": "Ergonomic Mouse", "category": "office", "price": 45, "tags": ["work", "computer"]},
        {"name": "Desk Lamp LED", "category": "office", "price": 35, "tags": ["lighting", "work"]},
        {"name": "Whiteboard 90x60", "category": "office", "price": 75, "tags": ["stationery", "meeting"]},
        {"name": "Paper Shredder", "category": "office", "price": 90, "tags": ["security", "document"]},
    # ---- Computers (mới, không trùng) ----
        {"name": "Alienware m18 R2", "category": "computer", "price": 2800, "tags": ["electronics", "gaming", "desktop-replacement"]},
        {"name": "Huawei MateBook X Pro", "category": "computer", "price": 1450, "tags": ["electronics", "ultrabook", "premium"]},
        {"name": "Chromebook Flex 5", "category": "computer", "price": 580, "tags": ["electronics", "chromeos", "convertible"]},
        {"name": "Gigabyte Aorus 17X", "category": "computer", "price": 2400, "tags": ["electronics", "gaming", "high-refresh"]},

        # ---- Phones (mới) ----
        {"name": "Vivo X100 Pro", "category": "phone", "price": 980, "tags": ["electronics", "camera", "zeiss"]},
        {"name": "Asus Zenfone 11 Ultra", "category": "phone", "price": 1100, "tags": ["electronics", "gaming", "compact"]},
        {"name": "Fairphone 5", "category": "phone", "price": 699, "tags": ["electronics", "sustainable", "repairable"]},
        {"name": "Nokia G60", "category": "phone", "price": 320, "tags": ["electronics", "budget", "durable"]},

        # ---- Drinks (mới) ----
        {"name": "Bubble Tea Taro", "category": "drink", "price": 4.5, "tags": ["beverage", "cold", "taiwanese"]},
        {"name": "Kombucha Ginger", "category": "drink", "price": 3.8, "tags": ["beverage", "healthy", "probiotic"]},
        {"name": "Cold Brew Coffee", "category": "drink", "price": 4.2, "tags": ["beverage", "cold", "coffee"]},
        {"name": "Herbal Infusion Mint", "category": "drink", "price": 2.9, "tags": ["beverage", "hot", "calming"]},

        # ---- Food (mới) ----
        {"name": "Tacos Al Pastor", "category": "food", "price": 11, "tags": ["meal", "mexican", "streetfood"]},
        {"name": "Biryani Chicken", "category": "food", "price": 16, "tags": ["meal", "indian", "rice"]},
        {"name": "Pho Bo Tai", "category": "food", "price": 13, "tags": ["meal", "vietnamese", "soup"]},
        {"name": "Quinoa Bowl", "category": "food", "price": 12, "tags": ["meal", "healthy", "superfood"]},

        # ---- Glasses (mới) ----
        {"name": "Zenni Optical Frames", "category": "glasses", "price": 25, "tags": ["vision", "budget", "online"]},
        {"name": "Maui Jim Sunglasses", "category": "glasses", "price": 250, "tags": ["fashion", "polarized", "beach"]},
        {"name": "Progressive Lenses", "category": "glasses", "price": 180, "tags": ["vision", "multifocal"]},

        # ---- Pants (mới) ----
        {"name": "Corduroy Pants Brown", "category": "pants", "price": 68, "tags": ["clothing", "casual", "retro"]},
        {"name": "Track Pants Reflective", "category": "pants", "price": 52, "tags": ["clothing", "sport", "night-run"]},
        {"name": "Palazzo Pants Floral", "category": "pants", "price": 48, "tags": ["clothing", "women", "summer"]},

        # ---- Shoes (mới) ----
        {"name": "Hoka One One Clifton", "category": "shoes", "price": 140, "tags": ["clothing", "running", "cushion"]},
        {"name": "Birkenstock Arizona", "category": "shoes", "price": 110, "tags": ["clothing", "comfort", "sandals"]},
        {"name": "Clarks Desert Boot", "category": "shoes", "price": 150, "tags": ["clothing", "casual", "classic"]},

        # ---- Shirts (mới) ----
        {"name": "Hawaiian Print Shirt", "category": "shirt", "price": 42, "tags": ["clothing", "summer", "vacation"]},
        {"name": "Thermal Long Sleeve", "category": "shirt", "price": 38, "tags": ["clothing", "winter", "base-layer"]},
        {"name": "Oxford Button Down", "category": "shirt", "price": 55, "tags": ["clothing", "smart", "office"]},

        # ---- Toys (mới) ----
        {"name": "Magnetic Tiles 100pcs", "category": "toy", "price": 65, "tags": ["kids", "stem", "building"]},
        {"name": "Squishmallow 12-inch", "category": "toy", "price": 25, "tags": ["kids", "plush", "collectible"]},
        {"name": "Science Experiment Kit", "category": "toy", "price": 35, "tags": ["kids", "education", "stem"]},

        # ---- Kitchen (mới) ----
        {"name": "Ninja Foodi Grill", "category": "kitchen", "price": 220, "tags": ["appliance", "multifunction", "indoor-grill"]},
        {"name": "Glass Food Containers Set", "category": "kitchen", "price": 40, "tags": ["storage", "mealprep"]},
        {"name": "Spice Rack 20 Jars", "category": "kitchen", "price": 55, "tags": ["organization", "cooking"]},

        # ---- Books (mới) ----
        {"name": "Project Hail Mary", "category": "book", "price": 28, "tags": ["scifi", "bestseller"]},
        {"name": "Educated", "category": "book", "price": 19, "tags": ["memoir", "inspiring"]},
        {"name": "JavaScript: The Good Parts", "category": "book", "price": 30, "tags": ["tech", "programming"]},

        # ---- Furniture (mới) ----
        {"name": "Recliner Chair Leather", "category": "furniture", "price": 680, "tags": ["home", "comfort", "livingroom"]},
        {"name": "Nightstand with USB", "category": "furniture", "price": 95, "tags": ["home", "bedroom", "smart"]},
        {"name": "Foldable Wall Desk", "category": "furniture", "price": 160, "tags": ["home", "small-space"]},

        # ---- Beauty (mới) ----
        {"name": "CeraVe Hydrating Cleanser", "category": "beauty", "price": 18, "tags": ["skincare", "gentle", "dermatologist"]},
        {"name": "Tom Ford Oud Wood", "category": "beauty", "price": 250, "tags": ["fragrance", "luxury", "unisex"]},
        {"name": "Anastasia Brow Wiz", "category": "beauty", "price": 25, "tags": ["makeup", "eyebrow"]},

        # ---- Accessories (mới) ----
        {"name": "Garmin Forerunner 265", "category": "accessory", "price": 450, "tags": ["wearable", "running", "gps"]},
        {"name": "Anker Power Bank 20000", "category": "accessory", "price": 60, "tags": ["electronics", "charging"]},
        {"name": "Kate Spade Tote Bag", "category": "accessory", "price": 180, "tags": ["fashion", "women", "handbag"]},

        # ---- Sports (mới) ----
        {"name": "Pull-up Bar Doorway", "category": "sport", "price": 45, "tags": ["fitness", "homegym"]},
        {"name": "Frisbee Ultimate Disc", "category": "sport", "price": 20, "tags": ["outdoor", "team-sport"]},
        {"name": "Resistance Bands Set", "category": "sport", "price": 35, "tags": ["fitness", "strength"]},

        # ---- Pet (mới) ----
        {"name": "Rabbit Hutch Outdoor", "category": "pet", "price": 140, "tags": ["pet", "rabbit", "housing"]},
        {"name": "Interactive Laser Toy", "category": "pet", "price": 28, "tags": ["pet", "cat", "play"]},
        {"name": "Pet Stroller", "category": "pet", "price": 95, "tags": ["pet", "travel", "small-dog"]},

        # ---- Garden (mới) ----
        {"name": "Rain Barrel 200L", "category": "garden", "price": 85, "tags": ["eco", "watering", "sustainable"]},
        {"name": "Hedge Trimmer Cordless", "category": "garden", "price": 120, "tags": ["tools", "landscaping"]},
        {"name": "Succulent Collection", "category": "garden", "price": 30, "tags": ["plants", "indoor", "low-maintenance"]},

        # ---- Health (mới) ----
        {"name": "Sleep Tracker Ring", "category": "health", "price": 299, "tags": ["wearable", "sleep", "data"]},
        {"name": "Aromatherapy Diffuser", "category": "health", "price": 45, "tags": ["wellness", "relaxation"]},
        {"name": "Posture Corrector", "category": "health", "price": 25, "tags": ["fitness", "back-support"]},

        # ---- Automotive (mới) ----
        {"name": "Roof Cargo Box 400L", "category": "automotive", "price": 320, "tags": ["car", "travel", "storage"]},
        {"name": "Snow Chains Set", "category": "automotive", "price": 90, "tags": ["car", "winter", "safety"]},
        {"name": "Backup Camera Wireless", "category": "automotive", "price": 75, "tags": ["car", "safety", "parking"]},

        # ---- DANH MỤC MỚI: Gaming ----
        {"name": "PlayStation 5 Pro", "category": "gaming", "price": 699, "tags": ["console", "4k", "nextgen"]},
        {"name": "Nintendo Switch OLED", "category": "gaming", "price": 350, "tags": ["console", "portable", "family"]},
        {"name": "Razer DeathAdder V3", "category": "gaming", "price": 75, "tags": ["peripheral", "mouse", "esports"]},
        {"name": "Logitech G Pro X Headset", "category": "gaming", "price": 130, "tags": ["audio", "mic", "competitive"]},

        # ---- DANH MỤC MỚI: Camping ----
        {"name": "Coleman 4-Person Tent", "category": "camping", "price": 180, "tags": ["outdoor", "shelter", "family"]},
        {"name": "Portable Camping Stove", "category": "camping", "price": 55, "tags": ["outdoor", "cooking"]},
        {"name": "Sleeping Bag -10°C", "category": "camping", "price": 85, "tags": ["outdoor", "winter"]},
        {"name": "Headlamp 300 Lumens", "category": "camping", "price": 30, "tags": ["outdoor", "lighting"]},

        # ---- DANH MỤC MỚI: Music ----
        {"name": "Fender Acoustic Guitar", "category": "music", "price": 220, "tags": ["instrument", "beginner"]},
        {"name": "Yamaha Digital Piano", "category": "music", "price": 580, "tags": ["instrument", "keys"]},
        {"name": "Vinyl Record Player", "category": "music", "price": 120, "tags": ["audio", "retro"]},
        {"name": "Ukulele Soprano", "category": "music", "price": 65, "tags": ["instrument", "portable"]},

        # ---- DANH MỤC MỚI: Photography ----
        {"name": "Canon EOS R10", "category": "photography", "price": 980, "tags": ["camera", "mirrorless", "vlog"]},
        {"name": "Tripod Carbon Fiber", "category": "photography", "price": 140, "tags": ["accessory", "stable"]},
        {"name": "Lens 50mm f1.8", "category": "photography", "price": 180, "tags": ["lens", "portrait"]},
        {"name": "Camera Bag Waterproof", "category": "photography", "price": 75, "tags": ["accessory", "protection"]},

        # ---- DANH MỤC MỚI: Art & Craft ----
        {"name": "Acrylic Paint Set 24", "category": "art", "price": 35, "tags": ["creative", "painting"]},
        {"name": "Sketchbook A4", "category": "art", "price": 15, "tags": ["drawing", "paper"]},
        {"name": "Calligraphy Pen Set", "category": "art", "price": 28, "tags": ["writing", "ink"]},

        # ---- DANH MỤC MỚI: Travel ----
        {"name": "Samsonite Luggage 24-inch", "category": "travel", "price": 180, "tags": ["luggage", "durable"]},
        {"name": "Travel Pillow Memory", "category": "travel", "price": 25, "tags": ["comfort", "flight"]},
        {"name": "Universal Adapter Plug", "category": "travel", "price": 18, "tags": ["electronics", "international"]},

        # ---- DANH MỤC MỚI: Smart Home ----
        {"name": "Google Nest Hub 2nd Gen", "category": "smarthome", "price": 95, "tags": ["smart", "display", "assistant"]},
        {"name": "Philips Hue Bulb Set", "category": "smarthome", "price": 60, "tags": ["lighting", "color"]},
        {"name": "Ring Video Doorbell", "category": "smarthome", "price": 130, "tags": ["security", "camera"]},
        {"name": "Smart Plug WiFi", "category": "smarthome", "price": 20, "tags": ["automation", "energy"]},
        
        # ---- Computers (mới hoàn toàn) ----
        {"name": "Panasonic Toughbook 55", "category": "computer", "price": 3200, "tags": ["electronics", "rugged", "enterprise"]},
        {"name": "Beelink Mini PC SER5", "category": "computer", "price": 420, "tags": ["electronics", "compact", "home-office"]},
        {"name": "Zotac ZBOX Magnus", "category": "computer", "price": 1100, "tags": ["electronics", "gaming", "mini"]},
        {"name": "Surface Pro 9", "category": "computer", "price": 1250, "tags": ["electronics", "2-in-1", "portable"]},

        # ---- Phones (mới) ----
        {"name": "Honor Magic 6 Pro", "category": "phone", "price": 1050, "tags": ["electronics", "camera", "ai"]},
        {"name": "Redmi Note 13 Pro+", "category": "phone", "price": 380, "tags": ["electronics", "budget", "200mp"]},
        {"name": "CAT S75", "category": "phone", "price": 599, "tags": ["electronics", "rugged", "satellite"]},
        {"name": "Blackview BV9200", "category": "phone", "price": 280, "tags": ["electronics", "outdoor", "battery"]},

        # ---- Drinks (mới) ----
        {"name": "Aloe Vera Drink Original", "category": "drink", "price": 2.2, "tags": ["beverage", "healthy", "refreshing"]},
        {"name": "Chai Latte Spiced", "category": "drink", "price": 4.1, "tags": ["beverage", "hot", "indian"]},
        {"name": "Sparkling Lemonade", "category": "drink", "price": 2.7, "tags": ["beverage", "cold", "citrus"]},
        {"name": "Protein Shake Vanilla", "category": "drink", "price": 3.9, "tags": ["beverage", "fitness", "post-workout"]},

        # ---- Food (mới) ----
        {"name": "Kimchi Fried Rice", "category": "food", "price": 12, "tags": ["meal", "korean", "spicy"]},
        {"name": "Butter Chicken Masala", "category": "food", "price": 15, "tags": ["meal", "indian", "creamy"]},
        {"name": "Greek Gyro Wrap", "category": "food", "price": 10, "tags": ["meal", "mediterranean", "streetfood"]},
        {"name": "Acai Bowl", "category": "food", "price": 9, "tags": ["meal", "healthy", "superfood"]},

        # ---- Glasses (mới) ----
        {"name": "Anti-Fog Safety Glasses", "category": "glasses", "price": 35, "tags": ["vision", "work", "protection"]},
        {"name": "Vintage Round Sunglasses", "category": "glasses", "price": 45, "tags": ["fashion", "retro"]},
        {"name": "Computer Glasses Yellow Tint", "category": "glasses", "price": 55, "tags": ["vision", "blue-light", "night"]},

        # ---- Pants (mới) ----
        {"name": "Linen Trousers White", "category": "pants", "price": 72, "tags": ["clothing", "summer", "breathable"]},
        {"name": "Hiking Pants Convertible", "category": "pants", "price": 78, "tags": ["clothing", "outdoor", "zip-off"]},
        {"name": "Wide Leg Culottes", "category": "pants", "price": 58, "tags": ["clothing", "women", "trendy"]},

        # ---- Shoes (mới) ----
        {"name": "On Cloud 5", "category": "shoes", "price": 130, "tags": ["clothing", "running", "cloudtech"]},
        {"name": "Crocs Classic Clog", "category": "shoes", "price": 50, "tags": ["clothing", "comfort", "casual"]},
        {"name": "Red Wing Iron Ranger", "category": "shoes", "price": 350, "tags": ["clothing", "boots", "heritage"]},

        # ---- Shirts (mới) ----
        {"name": "Camp Collar Shirt", "category": "shirt", "price": 48, "tags": ["clothing", "summer", "vacation"]},
        {"name": "Compression Base Layer", "category": "shirt", "price": 32, "tags": ["clothing", "sport", "performance"]},
        {"name": "Grandad Collar Shirt", "category": "shirt", "price": 45, "tags": ["clothing", "casual", "minimal"]},

        # ---- Toys (mới) ----
        {"name": "Wooden Train Set", "category": "toy", "price": 75, "tags": ["kids", "classic", "educational"]},
        {"name": "Fingerlings Monkey", "category": "toy", "price": 18, "tags": ["kids", "interactive", "pet"]},
        {"name": "Marble Run 150pcs", "category": "toy", "price": 55, "tags": ["kids", "stem", "construction"]},

        # ---- Kitchen (mới) ----
        {"name": "Sous Vide Precision Cooker", "category": "kitchen", "price": 110, "tags": ["appliance", "cooking", "pro"]},
        {"name": "Mandoline Slicer", "category": "kitchen", "price": 38, "tags": ["cookware", "prep", "safety"]},
        {"name": "Herb Keeper", "category": "kitchen", "price": 22, "tags": ["storage", "freshness"]},

        # ---- Books (mới) ----
        {"name": "The Psychology of Money", "category": "book", "price": 20, "tags": ["finance", "behavior"]},
        {"name": "1984 by George Orwell", "category": "book", "price": 14, "tags": ["fiction", "dystopia", "classic"]},
        {"name": "Deep Learning", "category": "book", "price": 65, "tags": ["tech", "ai", "advanced"]},

        # ---- Furniture (mới) ----
        {"name": "Bean Bag Chair XL", "category": "furniture", "price": 120, "tags": ["home", "comfort", "casual"]},
        {"name": "TV Stand 65-inch", "category": "furniture", "price": 210, "tags": ["home", "livingroom", "modern"]},
        {"name": "Ladder Shelf 5-Tier", "category": "furniture", "price": 135, "tags": ["home", "storage", "decor"]},

        # ---- Beauty (mới) ----
        {"name": "Retinol Night Cream", "category": "beauty", "price": 42, "tags": ["skincare", "anti-aging"]},
        {"name": "Jo Malone Peony", "category": "beauty", "price": 145, "tags": ["fragrance", "floral", "luxury"]},
        {"name": "Eyeshadow Palette Neutral", "category": "beauty", "price": 38, "tags": ["makeup", "versatile"]},

        # ---- Accessories (mới) ----
        {"name": "Whoop 4.0 Band", "category": "accessory", "price": 239, "tags": ["wearable", "fitness", "recovery"]},
        {"name": "Crossbody Phone Bag", "category": "accessory", "price": 35, "tags": ["fashion", "women", "handsfree"]},
        {"name": "Titanium Ring Matte", "category": "accessory", "price": 85, "tags": ["jewelry", "men", "minimal"]},

        # ---- Sports (mới) ----
        {"name": "Kettlebell 16kg", "category": "sport", "price": 68, "tags": ["fitness", "strength", "cast-iron"]},
        {"name": "Pickleball Paddle Set", "category": "sport", "price": 90, "tags": ["outdoor", "racket", "trending"]},
        {"name": "Speed Ladder 6m", "category": "sport", "price": 28, "tags": ["fitness", "agility", "training"]},

        # ---- Pet (mới) ----
        {"name": "Reptile Heat Lamp", "category": "pet", "price": 32, "tags": ["pet", "reptile", "uvb"]},
        {"name": "Pet Hair Remover Brush", "category": "pet", "price": 25, "tags": ["pet", "grooming", "reusable"]},
        {"name": "GPS Pet Tracker", "category": "pet", "price": 110, "tags": ["pet", "smart", "safety"]},

        # ---- Garden (mới) ----
        {"name": "Vertical Garden Wall", "category": "garden", "price": 95, "tags": ["plants", "indoor", "space-saving"]},
        {"name": "Mosquito Repellent Lantern", "category": "garden", "price": 48, "tags": ["outdoor", "pest-control"]},
        {"name": "Bonsai Starter Kit", "category": "garden", "price": 40, "tags": ["plants", "japanese", "art"]},

        # ---- Health (mới) ----
        {"name": "TENS Pain Relief Device", "category": "health", "price": 75, "tags": ["medical", "therapy"]},
        {"name": "Melatonin Gummies", "category": "health", "price": 15, "tags": ["supplement", "sleep"]},
        {"name": "Nasal Irrigator", "category": "health", "price": 45, "tags": ["medical", "sinus"]},

        # ---- Automotive (mới) ----
        {"name": "Car Seat Organizer", "category": "automotive", "price": 28, "tags": ["car", "storage", "family"]},
        {"name": "Tire Pressure Gauge Digital", "category": "automotive", "price": 22, "tags": ["car", "safety"]},
        {"name": "Car Cover Waterproof", "category": "automotive", "price": 65, "tags": ["car", "protection"]},

        # ---- Gaming (mở rộng) ----
        {"name": "Steam Deck OLED", "category": "gaming", "price": 549, "tags": ["console", "portable", "pc-gaming"]},
        {"name": "Corsair K70 RGB Pro", "category": "gaming", "price": 160, "tags": ["peripheral", "keyboard", "mechanical"]},
        {"name": "Elgato Stream Deck Mini", "category": "gaming", "price": 80, "tags": ["streaming", "control"]},

        # ---- Camping (mở rộng) ----
        {"name": "Inflatable Sleeping Pad", "category": "camping", "price": 70, "tags": ["outdoor", "comfort", "lightweight"]},
        {"name": "Camping Hammock Double", "category": "camping", "price": 55, "tags": ["outdoor", "relax"]},
        {"name": "Portable Solar Charger 20W", "category": "camping", "price": 65, "tags": ["outdoor", "power"]},

        # ---- Music (mở rộng) ----
        {"name": "Roland FP-30X Piano", "category": "music", "price": 720, "tags": ["instrument", "digital", "home"]},
        {"name": "Focusrite Scarlett 2i2", "category": "music", "price": 180, "tags": ["audio", "recording", "interface"]},
        {"name": "Cajon Drum", "category": "music", "price": 135, "tags": ["instrument", "percussion"]},

        # ---- Photography (mở rộng) ----
        {"name": "DJI Mini 4 Pro", "category": "photography", "price": 759, "tags": ["drone", "4k", "compact"]},
        {"name": "Godox Softbox 60cm", "category": "photography", "price": 85, "tags": ["lighting", "studio"]},
        {"name": "Memory Card 128GB UHS-II", "category": "photography", "price": 70, "tags": ["storage", "fast"]},

        # ---- Art & Craft (mở rộng) ----
        {"name": "Watercolor Pad A3", "category": "art", "price": 22, "tags": ["drawing", "paper", "thick"]},
        {"name": "Polymer Clay Kit", "category": "art", "price": 30, "tags": ["creative", "sculpture"]},
        {"name": "Embroidery Starter Set", "category": "art", "price": 38, "tags": ["craft", "needlework"]},

        # ---- Travel (mở rộng) ----
        {"name": "Packing Cubes Set", "category": "travel", "price": 28, "tags": ["luggage", "organization"]},
        {"name": "Neck Wallet RFID", "category": "travel", "price": 20, "tags": ["safety", "anti-theft"]},
        {"name": "Portable Espresso Maker", "category": "travel", "price": 55, "tags": ["coffee", "outdoor"]},

        # ---- Smart Home (mở rộng) ----
        {"name": "Eufy RoboVac 11S", "category": "smarthome", "price": 220, "tags": ["cleaning", "robot"]},
        {"name": "Aqara Smart Lock", "category": "smarthome", "price": 180, "tags": ["security", "keyless"]},
        {"name": "Govee LED Strip 5m", "category": "smarthome", "price": 45, "tags": ["lighting", "rgb"]},

        # ---- DANH MỤC MỚI: Cycling ----
        {"name": "Gravel Bike Carbon", "category": "cycling", "price": 1800, "tags": ["bike", "adventure", "offroad"]},
        {"name": "Bike Helmet MIPS", "category": "cycling", "price": 95, "tags": ["safety", "protection"]},
        {"name": "Bike Lock U-Lock", "category": "cycling", "price": 48, "tags": ["security", "anti-theft"]},
        {"name": "Cycling Jersey Summer", "category": "cycling", "price": 65, "tags": ["clothing", "performance"]},

        # ---- DANH MỤC MỚI: Fishing ----
        {"name": "Spinning Reel 3000", "category": "fishing", "price": 85, "tags": ["gear", "reel"]},
        {"name": "Fishing Rod Telescopic", "category": "fishing", "price": 55, "tags": ["gear", "portable"]},
        {"name": "Tackle Box 3600", "category": "fishing", "price": 35, "tags": ["storage", "organization"]},

        # ---- DANH MỤC MỚI: Home Decor ----
        {"name": "Macrame Wall Hanging", "category": "homedecor", "price": 45, "tags": ["decor", "boho"]},
        {"name": "Ceramic Vase Set", "category": "homedecor", "price": 60, "tags": ["decor", "modern"]},
        {"name": "Photo Frame Collage", "category": "homedecor", "price": 38, "tags": ["memory", "wall"]},

        # ---- DANH MỤC MỚI: Stationery ----
        {"name": "Fountain Pen Platinum", "category": "stationery", "price": 75, "tags": ["writing", "luxury"]},
        {"name": "Planner 2026 Leather", "category": "stationery", "price": 42, "tags": ["organization", "daily"]},
        {"name": "Highlighter Pastel Set", "category": "stationery", "price": 12, "tags": ["study", "colorful"]},

        # ---- DANH MỤC MỚI: DIY & Repair ----
        {"name": "Epoxy Resin Kit 1L", "category": "diy", "price": 55, "tags": ["craft", "resin-art"]},
        {"name": "Soldering Iron Kit", "category": "diy", "price": 40, "tags": ["electronics", "repair"]},
        {"name": "Wood Glue Strong", "category": "diy", "price": 15, "tags": ["repair", "furniture"]},
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
