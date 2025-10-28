"""
Product repository for MongoDB operations
"""
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class ProductRepository:
    def __init__(self, db):
        self.db = db
        self.collection = db.products

    async def create(self, product_data: dict) -> dict:
        """Create new product"""
        product_data["created_at"] = datetime.utcnow()
        product_data["updated_at"] = product_data["created_at"]
        
        result = await self.collection.insert_one(product_data)
        product_data["id"] = str(result.inserted_id)
        return product_data

    async def get(self, product_id: str) -> Optional[dict]:
        """Get single product by ID"""
        try:
            product = await self.collection.find_one({"_id": ObjectId(product_id)})
            if product:
                product["id"] = str(product.pop("_id"))
            return product
        except:
            return None

    async def get_all(self, skip: int = 0, limit: int = 10, category: Optional[str] = None) -> List[dict]:
        """Get all products with optional filtering"""
        query = {}
        if category:
            query["category"] = category
            
        cursor = self.collection.find(query).skip(skip).limit(limit)
        products = await cursor.to_list(None)
        
        # Convert _id to string id
        for product in products:
            product["id"] = str(product.pop("_id"))
            
        return products

    async def update(self, product_id: str, update_data: dict) -> Optional[dict]:
        """Update product"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(product_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["id"] = str(result.pop("_id"))
            return result
        except:
            return None

    async def delete(self, product_id: str) -> bool:
        """Delete product"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(product_id)})
            return result.deleted_count > 0
        except:
            return False