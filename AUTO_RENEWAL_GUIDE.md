# Auto-Renewal API Key - Hướng dẫn

## 🎯 Tổng quan

Hệ thống đã được tích hợp **tự động làm mới OpenRouter API key** khi key hết hạn hoặc không hợp lệ.

## ✨ Tính năng

### 1. **Tự động phát hiện key hết hạn**
- Phát hiện lỗi 401 Unauthorized từ OpenRouter
- Phát hiện các lỗi liên quan đến authentication
- Tự động trigger quá trình renewal

### 2. **Tự động tạo key mới**
- Sử dụng OpenRouter Provisioning API
- Tạo runtime key với tên tự động
- Lưu key mới vào database

### 3. **Tự động retry request**
- Sau khi tạo key mới, tự động retry request ban đầu
- Transparent cho user - không cần thao tác thủ công
- Log đầy đủ quá trình renewal

### 4. **Tự động provision key lần đầu**
- Nếu user chưa có API key, tự động tạo key mới
- Không cần user phải paste key thủ công

## 🔧 Cấu hình

### Bước 1: Set Provisioning Key

Để enable auto-renewal, bạn cần set biến môi trường:

```bash
# Windows PowerShell
$env:OPENROUTER_PROVISIONING_KEY="sk-or-v1-your-provisioning-key-here"

# Linux/Mac
export OPENROUTER_PROVISIONING_KEY="sk-or-v1-your-provisioning-key-here"
```

### Bước 2: Lấy Provisioning Key

1. Đăng nhập vào https://openrouter.ai/
2. Vào **Settings** → **API Keys**
3. Tạo một **Provisioning Key** (khác với Runtime Key)
4. Copy key và set vào biến môi trường

⚠️ **Lưu ý:** Provisioning Key có quyền tạo Runtime Keys, nên phải bảo mật tuyệt đối!

## 📋 Cách hoạt động

### Flow tự động renewal:

```
1. User chạy analysis
   ↓
2. System gọi OpenRouter API với key hiện tại
   ↓
3. OpenRouter trả về 401 (key hết hạn)
   ↓
4. System phát hiện lỗi 401
   ↓
5. System tự động gọi Provisioning API
   ↓
6. Tạo runtime key mới
   ↓
7. Lưu key mới vào database
   ↓
8. Retry request với key mới
   ↓
9. Trả kết quả cho user
```

### Flow khi chưa có key:

```
1. User chạy analysis lần đầu
   ↓
2. System kiểm tra database - không có key
   ↓
3. System tự động gọi Provisioning API
   ↓
4. Tạo runtime key mới
   ↓
5. Lưu vào database
   ↓
6. Gọi OpenRouter API với key mới
   ↓
7. Trả kết quả cho user
```

## 🔍 Monitoring & Logging

### Log messages:

```
[Auto-Renewal] Old key expired: ***************b465
[Auto-Renewal] Creating new runtime key for user 67123456...
[Auto-Renewal] ✅ New key created and saved: ***************a123
[Auto-Renewal] Key metadata: {'name': 'auto-renewed-67123456-20251005_154553', ...}
✅ API key was automatically renewed during this request
```

### Database tracking:

Mỗi lần auto-renew, database sẽ lưu:
```javascript
{
  "user_id": ObjectId("..."),
  "provider": "openrouter",
  "key_encrypted": "sk-or-v1-new-key",
  "auto_renewed": true,
  "last_renewal_at": ISODate("2025-10-05T08:45:53Z"),
  "updated_at": ISODate("2025-10-05T08:45:53Z")
}
```

## 🧪 Testing

### Test 1: Simulate key expiration

```python
# Trong analysis.py, tạm thời set key không hợp lệ
api_key = "sk-or-v1-invalid-key-for-testing"

# Chạy analysis
# System sẽ tự động phát hiện 401 và renew key
```

### Test 2: Test khi chưa có key

```python
# Xóa key khỏi database
from db import api_keys_col
from bson import ObjectId

api_keys_col().delete_one({
    "user_id": ObjectId("your-user-id"),
    "provider": "openrouter"
})

# Chạy analysis
# System sẽ tự động tạo key mới
```

### Test 3: Check auto-renewal từ script

```python
from api_key_auto_renewal import call_openrouter_with_auto_renewal

# Gọi với user_id
response = call_openrouter_with_auto_renewal(
    user_id="67123456789abcdef0123456",
    prompt="Test prompt"
)

# Kiểm tra response
if response.get("auto_renewed"):
    print("✅ Key was auto-renewed!")
if response.get("auto_renewal_failed"):
    print(f"❌ Auto-renewal failed: {response.get('auto_renewal_error')}")
```

## 🚨 Error Handling

### Khi auto-renewal thất bại:

```json
{
  "status": "error",
  "parsed": null,
  "raw": null,
  "error": "endpoint=https://openrouter.ai/api/v1/chat/completions error=401",
  "auto_renewal_failed": true,
  "auto_renewal_error": "OPENROUTER_PROVISIONING_KEY not set. Cannot auto-renew API key."
}
```

### Các trường hợp lỗi:

1. **Không có Provisioning Key**
   - Error: `OPENROUTER_PROVISIONING_KEY not set`
   - Giải pháp: Set biến môi trường

2. **Provisioning Key không hợp lệ**
   - Error: `401 Unauthorized` từ Provisioning API
   - Giải pháp: Kiểm tra lại provisioning key

3. **Hết quota**
   - Error: `Rate limit exceeded` hoặc `Insufficient credits`
   - Giải pháp: Nạp thêm credits vào OpenRouter account

4. **Network issues**
   - Error: `Failed to resolve 'openrouter.ai'`
   - Giải pháp: Kiểm tra kết nối internet

## 📊 Monitoring Dashboard

### Kiểm tra auto-renewal history:

```python
from db import api_keys_col
from bson import ObjectId

# Lấy thông tin key của user
key_doc = api_keys_col().find_one({
    "user_id": ObjectId("your-user-id"),
    "provider": "openrouter"
})

print(f"Auto-renewed: {key_doc.get('auto_renewed', False)}")
print(f"Last renewal: {key_doc.get('last_renewal_at')}")
print(f"Updated at: {key_doc.get('updated_at')}")
```

### Statistics:

```python
# Đếm số user đã được auto-renew
auto_renewed_count = api_keys_col().count_documents({
    "provider": "openrouter",
    "auto_renewed": True
})

print(f"Total auto-renewed keys: {auto_renewed_count}")
```

## 🔐 Security Best Practices

1. **Provisioning Key**
   - ⚠️ KHÔNG commit vào Git
   - ⚠️ KHÔNG hardcode trong code
   - ✅ Chỉ set qua biến môi trường
   - ✅ Rotate định kỳ (mỗi 3-6 tháng)

2. **Runtime Keys**
   - ✅ Được tạo tự động với tên unique
   - ✅ Có thể set limit để kiểm soát chi phí
   - ✅ Được log với masked format

3. **Database**
   - ⚠️ Trong production, nên encrypt API keys trước khi lưu
   - ✅ Set index unique trên (user_id, provider)
   - ✅ Backup định kỳ

## 🎓 Advanced Usage

### Custom renewal logic:

```python
from api_key_auto_renewal import auto_renew_api_key

# Tạo key mới với custom settings
result = auto_renew_api_key(
    user_id="67123456789abcdef0123456",
    old_key="sk-or-v1-old-key"
)

if result["success"]:
    print(f"New key: {result['new_key']}")
    print(f"Metadata: {result['meta']}")
```

### Manual key check:

```python
from api_key_auto_renewal import get_api_key_with_auto_renewal

# Lấy key (tự động tạo nếu chưa có)
result = get_api_key_with_auto_renewal("67123456789abcdef0123456")

if result["renewed"]:
    print("✅ New key was auto-provisioned")
print(f"API Key: {result['key']}")
```

## 📝 Changelog

### v1.0 (2025-10-05)
- ✅ Implement auto-renewal khi key hết hạn
- ✅ Tự động provision key lần đầu
- ✅ Logging với masked keys
- ✅ Error handling đầy đủ
- ✅ Database tracking
- ✅ Retry logic sau renewal

## 🆘 Troubleshooting

### Q: Auto-renewal không hoạt động?
**A:** Kiểm tra:
1. Đã set `OPENROUTER_PROVISIONING_KEY` chưa?
2. Provisioning key còn hợp lệ không?
3. Có đủ credits trong OpenRouter account không?
4. Check logs để xem error message cụ thể

### Q: Key bị renew quá nhiều lần?
**A:** Có thể do:
1. Key mới cũng bị invalid ngay
2. Provisioning key không có quyền tạo runtime keys
3. Network issues khiến request fail liên tục

### Q: Làm sao biết key đã được auto-renewed?
**A:** 
1. Check logs: `✅ API key was automatically renewed`
2. Check database: `auto_renewed: true`
3. Check response: `response.get("auto_renewed") == True`

---

**Tóm lại:** Hệ thống giờ đây hoàn toàn tự động quản lý API keys, user không cần lo lắng về việc key hết hạn! 🎉
