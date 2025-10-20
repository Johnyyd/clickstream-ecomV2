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


def get_api_key_with_auto_renewal_legacy(user_id):
    """
    Lấy API key cho user, tự động làm mới nếu cần
    
    Thứ tự ưu tiên:
    1. Key từ database (nếu có)
    2. Key từ file key.txt (nếu có)
    3. Key từ biến môi trường OPENROUTER_API_KEY (nếu có)
    4. Auto-provision key mới (nếu có OPENROUTER_PROVISIONING_KEY)
    
    Args:
        user_id: ID của user (string hoặc ObjectId)
    
    Returns:
        dict: {"key": str, "renewed": bool, "error": str}
    """
    try:
        # 1. Lấy key hiện tại từ database
        key_doc = api_keys_col().find_one(
            {"user_id": ObjectId(user_id), "provider": "openrouter"}
        )
        
        if key_doc:
            api_key = key_doc.get("key_encrypted", "")
            if api_key:
                return {
                    "key": api_key,
                    "renewed": False,
                    "error": None
                }
        
        # 2. Không có key trong DB, thử load từ file key.txt
        print(f"[Auto-Renewal] No API key in database for user {str(user_id)[:8]}")
        print(f"[Auto-Renewal] Attempting to load from key.txt or environment...")
        
        api_key = None
        source = None
        
        # Thử load từ file key.txt
        try:
            import os
            key_file = os.path.join(os.path.dirname(__file__), "key.txt")
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()
                    if api_key:
                        source = "key.txt"
                        print(f"[Auto-Renewal] ✅ Loaded API key from key.txt")
        except Exception as e:
            print(f"[Auto-Renewal] Could not read key.txt: {e}")
        
        # Nếu không có trong file, thử biến môi trường
        if not api_key:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                source = "environment variable"
                print(f"[Auto-Renewal] ✅ Loaded API key from OPENROUTER_API_KEY")
        
        # Nếu có key từ file hoặc env, lưu vào database
        if api_key:
            print(f"[Auto-Renewal] Saving API key from {source} to database...")
            from datetime import datetime
            import pytz
            now = datetime.now(pytz.UTC)
            api_keys_col().update_one(
                {"user_id": ObjectId(user_id), "provider": "openrouter"},
                {
                    "$set": {
                        "key_encrypted": api_key,
                        "updated_at": now,
                        "source": source
                    },
                    "$setOnInsert": {"created_at": now}
                },
                upsert=True
            )
            masked = ("*" * max(0, len(api_key) - 4)) + api_key[-4:] if len(api_key) > 4 else "****"
            print(f"[Auto-Renewal] ✅ API key saved to database: {masked}")
            
            return {
                "key": api_key,
                "renewed": True,
                "error": None
            }
        
        # 3. Không có key từ file/env, thử auto-provision
        print(f"[Auto-Renewal] No key in file or environment, attempting auto-provision...")
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
                "error": "No API key found. Please either:\n1. Add key to key.txt file\n2. Set OPENROUTER_API_KEY environment variable\n3. Set OPENROUTER_PROVISIONING_KEY for auto-provisioning"
            }
        
    except Exception as e:
        return {
            "key": None,
            "renewed": False,
            "error": str(e)
        }


# Wrapper cho openrouter_client để tự động retry với key mới
def call_openrouter_with_auto_renewal(user_id, prompt, model="qwen/qwen3-4b:free", max_tokens=2000, temperature=0.3):
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
    from api_key_manager import APIKeyManager
    
    # Lấy API key qua APIKeyManager (tự động sync và provision nếu cần)
    key_result = APIKeyManager.ensure_key_for_user(user_id, validate=False)
    
    if not key_result["key"]:
        return {
            "status": "error",
            "parsed": None,
            "raw": None,
            "error": key_result["error"] or "No API key available"
        }
    
    api_key = key_result["key"]
    # Track which key we actually use for the call (may be updated if auto-renew occurs)
    used_key = api_key
    
    # Gọi OpenRouter lần đầu
    print(f"[Auto-Renewal] Calling OpenRouter API...")
    response = call_openrouter(used_key, prompt, model, max_tokens, temperature)
    
    # Kiểm tra xem có lỗi 401/expired không
    if response.get("status") == "error" and is_key_expired_error(response.get("error")):
        print(f"[Auto-Renewal] ⚠️ API key expired, attempting auto-renewal...")
        
        # Thử làm mới key
        renewal_result = auto_renew_api_key(user_id, old_key=api_key)
        
        if renewal_result["success"]:
            # Retry với key mới
            new_key = renewal_result["new_key"]
            used_key = new_key
            print(f"[Auto-Renewal] Retrying with new key...")
            response = call_openrouter(used_key, prompt, model, max_tokens, temperature)
            
            # Thêm flag để biết đã auto-renew
            if response.get("status") == "ok":
                response["auto_renewed"] = True
        else:
            # Không thể làm mới, trả về lỗi
            response["auto_renewal_failed"] = True
            response["auto_renewal_error"] = renewal_result["error"]
    
    # If the model signaled truncation (finish_reason=length / truncated flag), attempt one continuation
    try:
        if response.get("status") == "ok" and response.get("truncated"):
            print("[Auto-Renewal] ⚠️ LLM output was truncated; attempting continuation call...")
            try:
                cont_prompt = (
                    "The previous response was truncated. Continue the JSON output ONLY so that when concatenated with the previous content it forms a single valid JSON object. "
                    "Do not add any explanations or markdown. Previous content:\n" + (response.get("content") or "")
                )
                cont_resp = call_openrouter(used_key, cont_prompt, model, max_tokens, temperature)
                if cont_resp.get("status") == "ok":
                    # Combine contents and attempt to parse combined JSON
                    combined = (response.get("content") or "") + (cont_resp.get("content") or "")
                    parsed_combined = None
                    try:
                        import json
                        if "{" in combined and "}" in combined:
                            start = combined.index("{")
                            end = combined.rindex("}") + 1
                            parsed_combined = json.loads(combined[start:end])
                    except Exception:
                        parsed_combined = None

                    if parsed_combined:
                        response["parsed"] = parsed_combined
                        response["auto_continued"] = True
                        response["raw"] = {"initial": response.get("raw"), "continuation": cont_resp.get("raw")}
                        response["content"] = combined
                        response["truncated"] = False
                        print("[Auto-Renewal] ✅ Continuation successful; reconstructed JSON from combined content.")
                    else:
                        response["continuation_raw"] = cont_resp.get("raw")
                        response["auto_continue_failed"] = True
                        print("[Auto-Renewal] ❌ Continuation attempt did not produce parseable JSON.")
            except Exception as e:
                response["auto_continue_failed"] = True
                response["auto_continue_error"] = str(e)
                print(f"[Auto-Renewal] ❌ Continuation attempt failed: {e}")
    except Exception:
        pass

    return response
