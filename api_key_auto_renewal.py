"""
API Key Auto-Renewal Module
Tự động làm mới OpenRouter API key khi hết hạn
"""
import os
from datetime import datetime
import pytz
from manage_API__key import create_runtime_key
from db import api_keys_col
from bson import ObjectId


def is_key_expired_error(error_message):
    """
    Kiểm tra xem lỗi có phải do API key hết hạn không
    """
    if not error_message:
        return False
    
    error_str = str(error_message).lower()
    
    # Các dấu hiệu cho thấy key hết hạn hoặc không hợp lệ
    expired_indicators = [
        "401",
        "unauthorized",
        "invalid api key",
        "expired",
        "authentication failed",
        "invalid_api_key"
    ]
    
    return any(indicator in error_str for indicator in expired_indicators)


def auto_renew_api_key(user_id, old_key=None):
    """
    Tự động tạo API key mới khi key cũ hết hạn
    
    Args:
        user_id: ID của user (string hoặc ObjectId)
        old_key: API key cũ (optional, để log)
    
    Returns:
        dict: {"success": bool, "new_key": str, "error": str}
    """
    try:
        # Kiểm tra xem có OPENROUTER_PROVISIONING_KEY không
        provisioning_key = os.getenv("OPENROUTER_PROVISIONING_KEY")
        if not provisioning_key:
            return {
                "success": False,
                "new_key": None,
                "error": "OPENROUTER_PROVISIONING_KEY not set. Cannot auto-renew API key."
            }
        
        # Tạo tên cho runtime key mới
        user_id_str = str(user_id)
        timestamp = datetime.now(pytz.UTC).strftime("%Y%m%d_%H%M%S")
        key_name = f"auto-renewed-{user_id_str[:8]}-{timestamp}"
        
        # Log old key (masked)
        if old_key:
            masked_old = ("*" * max(0, len(old_key) - 4)) + old_key[-4:] if len(old_key) > 4 else "****"
            print(f"[Auto-Renewal] Old key expired: {masked_old}")
        
        print(f"[Auto-Renewal] Creating new runtime key for user {user_id_str[:8]}...")
        
        # Tạo runtime key mới
        new_key, meta = create_runtime_key(name=key_name, limit=None)
        
        # Lưu vào database
        now = datetime.now(pytz.UTC)
        api_keys_col().update_one(
            {"user_id": ObjectId(user_id), "provider": "openrouter"},
            {
                "$set": {
                    "key_encrypted": new_key,
                    "updated_at": now,
                    "auto_renewed": True,
                    "last_renewal_at": now
                },
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )
        
        # Log success (masked)
        masked_new = ("*" * max(0, len(new_key) - 4)) + new_key[-4:] if len(new_key) > 4 else "****"
        print(f"[Auto-Renewal] ✅ New key created and saved: {masked_new}")
        print(f"[Auto-Renewal] Key metadata: {meta}")
        
        return {
            "success": True,
            "new_key": new_key,
            "error": None,
            "meta": meta
        }
        
    except Exception as e:
        error_msg = f"Failed to auto-renew API key: {str(e)}"
        print(f"[Auto-Renewal] ❌ {error_msg}")
        return {
            "success": False,
            "new_key": None,
            "error": error_msg
        }


def get_api_key_with_auto_renewal(user_id):
    """
    Lấy API key cho user, tự động làm mới nếu cần
    
    Args:
        user_id: ID của user (string hoặc ObjectId)
    
    Returns:
        dict: {"key": str, "renewed": bool, "error": str}
    """
    try:
        # Lấy key hiện tại từ database
        key_doc = api_keys_col().find_one(
            {"user_id": ObjectId(user_id), "provider": "openrouter"}
        )
        
        if not key_doc:
            # Không có key, thử tạo mới tự động
            print(f"[Auto-Renewal] No API key found for user {str(user_id)[:8]}, attempting auto-provision...")
            result = auto_renew_api_key(user_id)
            
            if result["success"]:
                return {
                    "key": result["new_key"],
                    "renewed": True,
                    "error": None
                }
            else:
                return {
                    "key": None,
                    "renewed": False,
                    "error": "No API key found and auto-provisioning failed"
                }
        
        # Có key, trả về
        api_key = key_doc.get("key_encrypted", "")
        return {
            "key": api_key,
            "renewed": False,
            "error": None if api_key else "API key is empty"
        }
        
    except Exception as e:
        return {
            "key": None,
            "renewed": False,
            "error": str(e)
        }


# Wrapper cho openrouter_client để tự động retry với key mới
def call_openrouter_with_auto_renewal(user_id, prompt, model="z-ai/glm-4.5-air:free", max_tokens=900, temperature=0.0):
    """
    Gọi OpenRouter API với tính năng tự động làm mới key khi hết hạn
    
    Args:
        user_id: ID của user
        prompt: Prompt để gửi
        model: Model name
        max_tokens: Max tokens
        temperature: Temperature
    
    Returns:
        dict: Response từ OpenRouter hoặc error
    """
    from openrouter_client import call_openrouter
    
    # Lấy API key (có thể tự động tạo mới nếu chưa có)
    key_result = get_api_key_with_auto_renewal(user_id)
    
    if not key_result["key"]:
        return {
            "status": "error",
            "parsed": None,
            "raw": None,
            "error": key_result["error"] or "No API key available"
        }
    
    api_key = key_result["key"]
    
    # Gọi OpenRouter lần đầu
    print(f"[Auto-Renewal] Calling OpenRouter API...")
    response = call_openrouter(api_key, prompt, model, max_tokens, temperature)
    
    # Kiểm tra xem có lỗi 401/expired không
    if response.get("status") == "error" and is_key_expired_error(response.get("error")):
        print(f"[Auto-Renewal] ⚠️ API key expired, attempting auto-renewal...")
        
        # Thử làm mới key
        renewal_result = auto_renew_api_key(user_id, old_key=api_key)
        
        if renewal_result["success"]:
            # Retry với key mới
            new_key = renewal_result["new_key"]
            print(f"[Auto-Renewal] Retrying with new key...")
            response = call_openrouter(new_key, prompt, model, max_tokens, temperature)
            
            # Thêm flag để biết đã auto-renew
            if response.get("status") == "ok":
                response["auto_renewed"] = True
        else:
            # Không thể làm mới, trả về lỗi
            response["auto_renewal_failed"] = True
            response["auto_renewal_error"] = renewal_result["error"]
    
    return response
