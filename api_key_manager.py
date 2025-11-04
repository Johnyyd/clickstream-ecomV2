"""
API Key Manager - Quản lý tập trung API keys cho OpenRouter
Xử lý: load, sync, validate, auto-provision
"""
import os
from datetime import datetime
import pytz
import requests
from app.core.db_sync import api_keys_col
from bson import ObjectId


def create_runtime_key(name: str, limit: int = None) -> tuple[str, dict]:
    """Create a new runtime API key through OpenRouter's provisioning API
    
    Args:
        name: Name for the new key
        limit: Optional credit limit
        
    Returns:
        Tuple of (key, metadata)
    """
    provisioning_key = os.getenv("OPENROUTER_PROVISIONING_KEY")
    if not provisioning_key:
        raise ValueError("OPENROUTER_PROVISIONING_KEY environment variable not set")
        
    url = "https://openrouter.ai/api/v1/auth/keys"
    payload = {"name": name}
    if limit is not None:
        payload["limit"] = limit
        
    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {provisioning_key}"}
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to create runtime key: {response.text}")
        
    data = response.json()
    return data["key"], data


class APIKeyManager:
    """Quản lý API keys cho OpenRouter"""
    
    PROVIDER = "openrouter"
    KEY_FILE = "key.txt"
    
    @staticmethod
    def _mask_key(key):
        """Mask API key để hiển thị an toàn"""
        if not key or len(key) < 8:
            return "****"
        return ("*" * (len(key) - 4)) + key[-4:]
    
    @staticmethod
    def _validate_key_format(key):
        """Kiểm tra format của OpenRouter key"""
        if not key:
            return False
        return key.startswith("sk-or-v1-") and len(key) > 20
    
    @staticmethod
    def load_key_from_file():
        """Load API key từ file key.txt"""
        try:
            key_file = os.path.join(os.path.dirname(__file__), APIKeyManager.KEY_FILE)
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    key = f.read().strip()
                    if key and APIKeyManager._validate_key_format(key):
                        print(f"[KeyManager] ✅ Loaded key from {APIKeyManager.KEY_FILE}: {APIKeyManager._mask_key(key)}")
                        return key
                    elif key:
                        print(f"[KeyManager] ⚠️ Invalid key format in {APIKeyManager.KEY_FILE}")
        except Exception as e:
            print(f"[KeyManager] ⚠️ Could not read {APIKeyManager.KEY_FILE}: {e}")
        return None
    
    @staticmethod
    def load_key_from_env():
        """Load API key từ biến môi trường"""
        key = os.getenv("OPENROUTER_API_KEY")
        if key and APIKeyManager._validate_key_format(key):
            print(f"[KeyManager] ✅ Loaded key from OPENROUTER_API_KEY: {APIKeyManager._mask_key(key)}")
            return key
        elif key:
            print(f"[KeyManager] ⚠️ Invalid key format in OPENROUTER_API_KEY")
        return None
    
    @staticmethod
    def load_key_from_db(user_id):
        """Load API key từ database cho user"""
        try:
            key_doc = api_keys_col().find_one({
                "user_id": ObjectId(user_id),
                "provider": APIKeyManager.PROVIDER
            })
            
            if key_doc:
                key = key_doc.get("key_encrypted", "")
                if key and APIKeyManager._validate_key_format(key):
                    print(f"[KeyManager] ✅ Loaded key from database: {APIKeyManager._mask_key(key)}")
                    return key
                elif key:
                    print(f"[KeyManager] ⚠️ Invalid key format in database")
        except Exception as e:
            print(f"[KeyManager] ⚠️ Error loading key from database: {e}")
        return None
    
    @staticmethod
    def save_key_to_db(user_id, api_key, source="manual"):
        """Lưu API key vào database"""
        try:
            if not APIKeyManager._validate_key_format(api_key):
                print(f"[KeyManager] ❌ Invalid key format, not saving")
                return False
            
            now = datetime.now(pytz.UTC)
            result = api_keys_col().update_one(
                {"user_id": ObjectId(user_id), "provider": APIKeyManager.PROVIDER},
                {
                    "$set": {
                        "key_encrypted": api_key,
                        "updated_at": now,
                        "source": source,
                        "last_validated": now
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            
            masked = APIKeyManager._mask_key(api_key)
            print(f"[KeyManager] ✅ Saved key to database (source: {source}): {masked}")
            return True
            
        except Exception as e:
            print(f"[KeyManager] ❌ Error saving key to database: {e}")
            return False
    
    @staticmethod
    def auto_provision_key(user_id):
        """Tự động tạo runtime key mới qua Provisioning API"""
        try:
            
            provisioning_key = os.getenv("OPENROUTER_PROVISIONING_KEY")
            if not provisioning_key:
                print(f"[KeyManager] ⚠️ OPENROUTER_PROVISIONING_KEY not set, cannot auto-provision")
                return None
            
            user_id_str = str(user_id)
            timestamp = datetime.now(pytz.UTC).strftime("%Y%m%d_%H%M%S")
            key_name = f"auto-{user_id_str[:8]}-{timestamp}"
            
            print(f"[KeyManager] 🔄 Auto-provisioning new key for user {user_id_str[:8]}...")
            
            new_key, meta = create_runtime_key(name=key_name, limit=None)
            
            masked = APIKeyManager._mask_key(new_key)
            print(f"[KeyManager] ✅ Auto-provisioned new key: {masked}")
            print(f"[KeyManager]    Metadata: {meta}")
            
            # Lưu vào database
            APIKeyManager.save_key_to_db(user_id, new_key, source="auto-provisioned")
            
            return new_key
            
        except Exception as e:
            print(f"[KeyManager] ❌ Auto-provision failed: {e}")
            return None
    
    @staticmethod
    def sync_and_get_key(user_id):
        """
        Đồng bộ và lấy API key cho user theo thứ tự ưu tiên:
        1. Key từ database (ưu tiên cao nhất)
        2. Key từ file key.txt
        3. Key từ biến môi trường OPENROUTER_API_KEY
        4. Auto-provision key mới (nếu có OPENROUTER_PROVISIONING_KEY)
        
        Nếu key từ file/env khác với DB, sẽ sync vào DB.
        
        Returns:
            dict: {
                "key": str,
                "source": str,
                "synced": bool,
                "error": str
            }
        """
        print(f"\n[KeyManager] ===== Syncing API key for user {str(user_id)[:8]} =====")
        
        # 1. Kiểm tra key trong database
        db_key = APIKeyManager.load_key_from_db(user_id)
        
        # 2. Load key từ các nguồn khác
        file_key = APIKeyManager.load_key_from_file()
        env_key = APIKeyManager.load_key_from_env()
        
        # Xác định key nào sẽ dùng
        selected_key = None
        source = None
        synced = False
        
        # Ưu tiên: DB > File > Env > Auto-provision
        if db_key:
            # Có key trong DB rồi
            selected_key = db_key
            source = "database"
            
            # Kiểm tra xem có cần sync từ file/env không
            if file_key and file_key != db_key:
                print(f"[KeyManager] ⚠️ Key in file differs from database")
                print(f"[KeyManager] 💡 Keeping database key (priority)")
            
            if env_key and env_key != db_key:
                print(f"[KeyManager] ⚠️ Key in environment differs from database")
                print(f"[KeyManager] 💡 Keeping database key (priority)")
        
        elif file_key:
            # Không có trong DB, dùng key từ file
            selected_key = file_key
            source = "key.txt"
            synced = True
            APIKeyManager.save_key_to_db(user_id, file_key, source="key.txt")
        
        elif env_key:
            # Không có trong DB và file, dùng key từ env
            selected_key = env_key
            source = "environment"
            synced = True
            APIKeyManager.save_key_to_db(user_id, env_key, source="environment")
        
        else:
            # Không có key nào, thử auto-provision
            print(f"[KeyManager] ⚠️ No API key found in database, file, or environment")
            print(f"[KeyManager] 🔄 Attempting auto-provision...")
            
            provisioned_key = APIKeyManager.auto_provision_key(user_id)
            
            if provisioned_key:
                selected_key = provisioned_key
                source = "auto-provisioned"
                synced = True
            else:
                print(f"[KeyManager] ❌ No API key available")
                return {
                    "key": None,
                    "source": None,
                    "synced": False,
                    "error": "No API key found. Please:\n1. Add key to key.txt\n2. Set OPENROUTER_API_KEY env var\n3. Set OPENROUTER_PROVISIONING_KEY for auto-provision"
                }
        
        print(f"[KeyManager] ✅ Using key from: {source}")
        if synced:
            print(f"[KeyManager] ✅ Key synced to database")
        print(f"[KeyManager] ===== Sync complete =====\n")
        
        return {
            "key": selected_key,
            "source": source,
            "synced": synced,
            "error": None
        }
    
    @staticmethod
    def validate_key_with_api(api_key):
        """
        Validate API key bằng cách gọi OpenRouter API
        Returns: (is_valid: bool, error_message: str)
        """
        try:
            import requests
            
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Clickstream Dashboard"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[KeyManager] ✅ Key validated successfully")
                return True, None
            elif response.status_code == 401:
                error = "Key is invalid or expired"
                print(f"[KeyManager] ❌ {error}")
                return False, error
            elif response.status_code == 402:
                error = "Out of credits"
                print(f"[KeyManager] ❌ {error}")
                return False, error
            else:
                error = f"Unexpected status: {response.status_code}"
                print(f"[KeyManager] ⚠️ {error}")
                return False, error
                
        except Exception as e:
            error = f"Validation error: {str(e)}"
            print(f"[KeyManager] ❌ {error}")
            return False, error
    
    @staticmethod
    def ensure_key_for_user(user_id, validate=False):
        """
        Đảm bảo user có API key hợp lệ
        - Sync key từ các nguồn
        - Optionally validate với OpenRouter API
        
        Returns:
            dict: {
                "key": str,
                "source": str,
                "valid": bool,
                "error": str
            }
        """
        # Sync và lấy key
        result = APIKeyManager.sync_and_get_key(user_id)
        
        if not result["key"]:
            return {
                "key": None,
                "source": None,
                "valid": False,
                "error": result["error"]
            }
        
        # Validate nếu được yêu cầu
        valid = True
        error = None
        
        if validate:
            print(f"[KeyManager] 🔍 Validating key with OpenRouter API...")
            valid, error = APIKeyManager.validate_key_with_api(result["key"])
        
        return {
            "key": result["key"],
            "source": result["source"],
            "valid": valid,
            "error": error
        }


# Convenience functions
def get_user_api_key(user_id, validate=False):
    """
    Lấy API key cho user (convenience function)
    
    Args:
        user_id: User ID
        validate: Có validate key với API không
    
    Returns:
        str: API key hoặc None
    """
    result = APIKeyManager.ensure_key_for_user(user_id, validate=validate)
    return result["key"]


def sync_user_api_key(user_id):
    """
    Đồng bộ API key cho user (convenience function)
    
    Args:
        user_id: User ID
    
    Returns:
        dict: Result từ sync_and_get_key
    """
    return APIKeyManager.sync_and_get_key(user_id)
