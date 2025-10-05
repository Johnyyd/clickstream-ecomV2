#!/usr/bin/env python3
"""
Test script để demo tính năng Auto-Renewal API Key
"""
import os
from db import api_keys_col, users_col
from bson import ObjectId
from api_key_auto_renewal import (
    auto_renew_api_key,
    get_api_key_with_auto_renewal,
    call_openrouter_with_auto_renewal,
    is_key_expired_error
)


def test_is_key_expired_error():
    """Test hàm phát hiện lỗi key hết hạn"""
    print("\n=== Test 1: Phát hiện lỗi key hết hạn ===")
    
    test_cases = [
        ("401 Unauthorized", True),
        ("Invalid API key", True),
        ("Authentication failed", True),
        ("endpoint=https://openrouter.ai error=401", True),
        ("Rate limit exceeded", False),
        ("Network error", False),
        (None, False),
    ]
    
    for error_msg, expected in test_cases:
        result = is_key_expired_error(error_msg)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{error_msg}' -> {result} (expected {expected})")


def test_get_api_key():
    """Test lấy API key với auto-renewal"""
    print("\n=== Test 2: Lấy API key với auto-renewal ===")
    
    # Lấy user đầu tiên
    user = users_col().find_one({})
    if not user:
        print("❌ Không tìm thấy user nào trong database")
        return
    
    user_id = user["_id"]
    username = user.get("username", "N/A")
    
    print(f"Testing với user: {username} ({user_id})")
    
    # Test lấy key
    result = get_api_key_with_auto_renewal(user_id)
    
    if result["key"]:
        masked = ("*" * max(0, len(result["key"]) - 4)) + result["key"][-4:]
        print(f"✅ API Key: {masked}")
        print(f"   Renewed: {result['renewed']}")
        print(f"   Error: {result['error']}")
    else:
        print(f"❌ Không lấy được key: {result['error']}")


def test_manual_renewal():
    """Test tạo key mới thủ công"""
    print("\n=== Test 3: Manual renewal ===")
    
    # Kiểm tra provisioning key
    if not os.getenv("OPENROUTER_PROVISIONING_KEY"):
        print("⚠️  OPENROUTER_PROVISIONING_KEY chưa được set")
        print("   Auto-renewal sẽ không hoạt động")
        return
    
    # Lấy user đầu tiên
    user = users_col().find_one({})
    if not user:
        print("❌ Không tìm thấy user nào trong database")
        return
    
    user_id = user["_id"]
    username = user.get("username", "N/A")
    
    print(f"Attempting manual renewal cho user: {username}")
    
    # Lấy old key nếu có
    key_doc = api_keys_col().find_one({"user_id": user_id, "provider": "openrouter"})
    old_key = key_doc.get("key_encrypted") if key_doc else None
    
    # Thử renew
    result = auto_renew_api_key(user_id, old_key)
    
    if result["success"]:
        masked = ("*" * max(0, len(result["new_key"]) - 4)) + result["new_key"][-4:]
        print(f"✅ Renewal thành công!")
        print(f"   New key: {masked}")
        print(f"   Metadata: {result['meta']}")
    else:
        print(f"❌ Renewal thất bại: {result['error']}")


def test_full_flow():
    """Test full flow: xóa key -> auto-provision -> gọi API"""
    print("\n=== Test 4: Full auto-renewal flow ===")
    
    # Kiểm tra provisioning key
    if not os.getenv("OPENROUTER_PROVISIONING_KEY"):
        print("⚠️  OPENROUTER_PROVISIONING_KEY chưa được set")
        print("   Skip test này")
        return
    
    # Lấy user đầu tiên
    user = users_col().find_one({})
    if not user:
        print("❌ Không tìm thấy user nào trong database")
        return
    
    user_id = str(user["_id"])
    username = user.get("username", "N/A")
    
    print(f"Testing full flow với user: {username}")
    
    # Bước 1: Xóa key hiện tại (để test auto-provision)
    print("\n1. Xóa key hiện tại...")
    result = api_keys_col().delete_one({"user_id": ObjectId(user_id), "provider": "openrouter"})
    print(f"   Deleted {result.deleted_count} key(s)")
    
    # Bước 2: Gọi OpenRouter API (sẽ tự động tạo key mới)
    print("\n2. Gọi OpenRouter API (sẽ auto-provision key)...")
    test_prompt = "Say hello in JSON format with key 'message'"
    
    response = call_openrouter_with_auto_renewal(
        user_id=user_id,
        prompt=test_prompt,
        model="z-ai/glm-4.5-air:free",
        max_tokens=100,
        temperature=0.0
    )
    
    # Bước 3: Kiểm tra kết quả
    print("\n3. Kết quả:")
    print(f"   Status: {response.get('status')}")
    
    if response.get("auto_renewed"):
        print("   ✅ Key đã được auto-renewed!")
    
    if response.get("auto_renewal_failed"):
        print(f"   ❌ Auto-renewal failed: {response.get('auto_renewal_error')}")
    
    if response.get("status") == "ok":
        print("   ✅ API call thành công!")
        if response.get("parsed"):
            print(f"   Parsed response: {response['parsed']}")
    else:
        print(f"   ❌ API call failed: {response.get('error')}")
    
    # Bước 4: Verify key đã được lưu vào database
    print("\n4. Verify database:")
    key_doc = api_keys_col().find_one({"user_id": ObjectId(user_id), "provider": "openrouter"})
    if key_doc:
        masked = ("*" * max(0, len(key_doc["key_encrypted"]) - 4)) + key_doc["key_encrypted"][-4:]
        print(f"   ✅ Key found in database: {masked}")
        print(f"   Auto-renewed: {key_doc.get('auto_renewed', False)}")
        print(f"   Last renewal: {key_doc.get('last_renewal_at')}")
    else:
        print("   ❌ Không tìm thấy key trong database")


def show_current_status():
    """Hiển thị trạng thái hiện tại của tất cả users"""
    print("\n=== Trạng thái API Keys hiện tại ===")
    
    users = list(users_col().find({}, {"username": 1, "email": 1}))
    
    for user in users:
        user_id = user["_id"]
        username = user.get("username", "N/A")
        
        key_doc = api_keys_col().find_one({"user_id": user_id, "provider": "openrouter"})
        
        print(f"\nUser: {username}")
        if key_doc:
            key = key_doc.get("key_encrypted", "")
            masked = ("*" * max(0, len(key) - 4)) + key[-4:] if key else "N/A"
            print(f"  ✅ Has key: {masked}")
            print(f"     Auto-renewed: {key_doc.get('auto_renewed', False)}")
            print(f"     Last renewal: {key_doc.get('last_renewal_at', 'N/A')}")
            print(f"     Updated: {key_doc.get('updated_at', 'N/A')}")
        else:
            print(f"  ❌ No API key")


def main():
    """Main test runner"""
    print("=" * 60)
    print("AUTO-RENEWAL API KEY - TEST SUITE")
    print("=" * 60)
    
    # Kiểm tra provisioning key
    has_provisioning = bool(os.getenv("OPENROUTER_PROVISIONING_KEY"))
    print(f"\nProvisioning Key: {'✅ Set' if has_provisioning else '❌ Not set'}")
    
    if not has_provisioning:
        print("\n⚠️  WARNING: OPENROUTER_PROVISIONING_KEY chưa được set!")
        print("   Một số test sẽ bị skip.")
        print("\n   Để enable auto-renewal, chạy:")
        print("   $env:OPENROUTER_PROVISIONING_KEY='sk-or-v1-your-provisioning-key'")
    
    # Hiển thị trạng thái hiện tại
    show_current_status()
    
    # Chạy các test
    test_is_key_expired_error()
    test_get_api_key()
    
    if has_provisioning:
        test_manual_renewal()
        
        # Hỏi user có muốn chạy full test không (vì nó sẽ xóa key hiện tại)
        print("\n" + "=" * 60)
        response = input("Chạy full flow test (sẽ xóa key hiện tại)? (y/N): ")
        if response.lower() == 'y':
            test_full_flow()
        else:
            print("Skip full flow test")
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
