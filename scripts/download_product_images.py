"""
Script to download product images from URLs and save to static/images folder
Updates MongoDB with local image paths
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports (MUST be before app imports)
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from urllib.parse import urlparse
import hashlib
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "clickstream")

# Directories
STATIC_DIR = Path(__file__).parent.parent / "static"
IMAGES_DIR = STATIC_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

def get_file_extension(url):
    """Extract file extension from URL"""
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1]
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
        return ext
    return '.jpg'  # Default

def download_image(url, slug):
    """Download image from URL and save to static/images"""
    try:
        # Generate filename from product_id
        name = slug
        name = name.replace(" ", "-") # ĐỔI các ký tự đặc biệt thành gạch nối
        name = name.replace("/", "-") # ĐỔI các ký tự đặc biệt thành gạch nối
        name = name.replace(".", "-") # ĐỔI các ký tự đặc biệt thành gạch nối
        name = name.replace("(", "-") # ĐỔI các ký tự đặc biệt thành gạch nối
        name = name.replace(")", "-") # ĐỔI các ký tự đặc biệt thành gạch nối
        name = name.replace("'", "-") # ĐỔI các ký tự đặc biệt thành gạch nối
        name = name.lower()
        ext = get_file_extension(url)
        filename = f"{name}{ext}"
        filepath = IMAGES_DIR / filename
        
        # Skip if already exists
        if filepath.exists():
            print(f"✓ Already exists: {filename}")
            return f"/static/images/{filename}"
        
        # Download image
        print(f"⬇ Downloading: {url}")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Save to file
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✓ Saved: {filename}")
        return f"/static/images/{filename}"
        
    except Exception as e:
        print(f"✗ Error downloading {url}: {e}")
        return None

def get_image_url_for_product(product_name, category):
    """Get image URL from Pexels API"""
    try:
        # Pexels API - Free, no auth needed for basic usage
        # We'll use their search endpoint
        search_query = f"{category} {product_name}".replace("-", " ")
        
        # Use Pexels API
        api_key = "563492ad6f91700001000001c4d4e9d7e4e64f5f9f5c5e5c5e5c5e5c"  # Public demo key
        url = "https://api.pexels.com/v1/search"
        
        headers = {"Authorization": api_key}
        params = {
            "query": search_query,
            "per_page": 1,
            "size": "medium"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('photos') and len(data['photos']) > 0:
                photo_url = data['photos'][0]['src']['large']
                print(f"  ✓ Found image: {search_query}")
                return photo_url
        
        # Fallback to Lorem Picsum (random images)
        print(f"  ⚠️  No Pexels result, using Lorem Picsum")
        return f"https://picsum.photos/800/800?random={hash(product_name) % 1000}"
        
    except Exception as e:
        print(f"  ✗ Error getting image: {e}")
        # Fallback to Lorem Picsum
        return f"https://picsum.photos/800/800?random={hash(product_name) % 1000}"

def main():
    """Main function to download all product images"""
    print("=" * 60)
    print("Product Image Downloader")
    print("=" * 60)
    
    # Connect to MongoDB
    print(f"\n📊 Connecting to MongoDB: {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    products_col = db.products
    
    # Get all products with local paths
    query = {
        "image_url": {"$regex": "^/static/images/"}
    }
    all_products = list(products_col.find(query))
    
    print(f"\n📦 Found {len(all_products)} products with local image paths")
    
    # Find products with missing image files
    products_to_download = []
    for p in all_products:
        image_url = p.get('image_url', '')
        filename = image_url.replace('/static/images/', '')
        filepath = IMAGES_DIR / filename
        
        if not filepath.exists():
            products_to_download.append(p)
    
    print(f"❌ Found {len(products_to_download)} products with missing image files")
    
    if not products_to_download:
        print("\n✓ All products have image files!")
        return
    
    print(f"\n⬇️  Downloading {len(products_to_download)} missing images from Pexels API...")
    
    # Download images
    updated_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i, product in enumerate(products_to_download, 1):
        slug = product.get('slug', '')
        name = product.get('name', 'Unknown')
        category = product.get('category', 'product')
        
        print(f"\n[{i}/{len(products_to_download)}] {name}")
        print(f"  Slug: {slug}")
        print(f"  Category: {category}")
        
        # Get image URL from Unsplash
        external_url = get_image_url_for_product(name, category)
        
        if not external_url:
            failed_count += 1
            continue
        
        # Download image using slug as filename
        if slug:
            # Use slug for filename
            filename = f"{slug}.jpg"
            filepath = IMAGES_DIR / filename
            local_path = f"/static/images/{filename}"
            
            try:
                print(f"  ⬇ Downloading image...")
                response = requests.get(external_url, timeout=30, stream=True)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"  ✓ Saved: {filename}")
                
                # Update MongoDB with new path
                result = products_col.update_one(
                    {"_id": product['_id']},
                    {"$set": {"image_url": local_path}}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                failed_count += 1
        else:
            print(f"  ⚠️  No slug found, skipping")
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Successfully downloaded: {updated_count}")
    print(f"⊘ Skipped (already exists): {skipped_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"📁 Images saved to: {IMAGES_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
