# 🔑 Hệ thống Quản lý API Key - Tài liệu

## 📋 Tổng quan

Hệ thống quản lý API key tập trung với **APIKeyManager** - tự động sync, validate và provision keys.

## 🎯 Quy trình hoạt động

### **Khi User Login:**

```
User login
    ↓
[APIKeyManager] Sync API key
    ↓
Kiểm tra thứ tự ưu tiên:
    1. Key trong Database ✅ (ưu tiên cao nhất)
    2. Key trong key.txt
    3. Key trong OPENROUTER_API_KEY (env)
    4. Auto-provision (nếu có OPENROUTER_PROVISIONING_KEY)
    ↓
Đồng bộ vào Database
    ↓
Trả về key cho user
```

### **Thứ tự ưu tiên:**

1. **Database** (cao nhất) - Key đã được lưu trữ
2. **key.txt** - File local
3. **Environment Variable** - OPENROUTER_API_KEY
4. **Auto-provision** - Tạo mới tự động

### **Sync Logic:**

- ✅ Nếu có key trong DB → Dùng key đó (không sync từ file/env)
- ✅ Nếu không có trong DB → Load từ file/env → Lưu vào DB
- ✅ Nếu không có ở đâu cả → Auto-provision (nếu có provisioning key)

## 📁 Cấu trúc Files

### **Core Module:**
- `api_key_manager.py` - Module quản lý tập trung (MỚI)

### **Supporting Modules:**
- `api_key_auto_renewal.py` - Auto-renewal và retry logic
- `manage_API__key.py` - Provisioning API wrapper

### **Integration:**
- `server.py` - Login endpoint với auto-sync
- `analysis.py` - Sử dụng key khi analyze
- `static/dashboard.js` - Hiển thị key status

## 🔧 APIKeyManager - Chi tiết

### **Class Methods:**

#### 1. `sync_and_get_key(user_id)`
Đồng bộ và lấy key cho user.

```python
from api_key_manager import APIKeyManager

result = APIKeyManager.sync_and_get_key(user_id)
# Returns: {
#     "key": "sk-or-v1-...",
#     "source": "database|key.txt|environment|auto-provisioned",
#     "synced": True/False,
#     "error": None
# }
```

#### 2. `ensure_key_for_user(user_id, validate=False)`
Đảm bảo user có key hợp lệ, optionally validate với API.

```python
result = APIKeyManager.ensure_key_for_user(user_id, validate=True)
# Returns: {
#     "key": "sk-or-v1-...",
#     "source": "database",
#     "valid": True,
#     "error": None
# }
```

#### 3. `validate_key_with_api(api_key)`
Validate key bằng cách gọi OpenRouter API.

```python
is_valid, error = APIKeyManager.validate_key_with_api(api_key)
```

#### 4. `save_key_to_db(user_id, api_key, source)`
Lưu key vào database.

```python
success = APIKeyManager.save_key_to_db(user_id, api_key, source="manual")
```

#### 5. `auto_provision_key(user_id)`
Tự động tạo runtime key mới.

```python
new_key = APIKeyManager.auto_provision_key(user_id)
```

### **Convenience Functions:**

```python
from api_key_manager import get_user_api_key, sync_user_api_key

# Lấy key đơn giản
key = get_user_api_key(user_id)

# Sync key
result = sync_user_api_key(user_id)
```

## 🚀 Cách sử dụng

### **Option 1: Sử dụng file key.txt (Đơn giản nhất)**

1. Tạo file `key.txt` trong root directory:
   ```
   sk-or-v1-your-api-key-here
   ```

2. Start server:
   ```powershell
   python server.py
   ```

3. Login → Key tự động load và sync vào DB

### **Option 2: Sử dụng Environment Variable**

```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-your-key"
python server.py
```

### **Option 3: Auto-provisioning**

```powershell
$env:OPENROUTER_PROVISIONING_KEY="sk-or-v1-your-provisioning-key"
python server.py
```

Khi login, nếu không có key, hệ thống tự động tạo mới.

## 📊 Login Flow

### **Request:**
```http
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

### **Response:**
```json
{
  "token": "session-token-here",
  "user_id": "68e228e87f803a11a4e23045",
  "username": "admin",
  "api_key_status": {
    "has_key": true,
    "source": "key.txt",
    "synced": true
  }
}
```

### **Console Logs:**
```
[Login] User admin logged in, syncing API key...
[KeyManager] ===== Syncing API key for user 68e228e8 =====
[KeyManager] ✅ Loaded key from key.txt: ***************b465
[KeyManager] ✅ Saved key to database (source: key.txt): ***************b465
[KeyManager] ✅ Using key from: key.txt
[KeyManager] ✅ Key synced to database
[KeyManager] ===== Sync complete =====
[Login] ✅ API key ready: ***************b465 (source: key.txt)
```

## 🔍 Database Schema

### **Collection: api_keys**
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "provider": "openrouter",
  "key_encrypted": "sk-or-v1-...",
  "source": "key.txt|environment|auto-provisioned|manual",
  "created_at": ISODate("2025-10-05T09:00:00Z"),
  "updated_at": ISODate("2025-10-05T09:30:00Z"),
  "last_validated": ISODate("2025-10-05T09:30:00Z")
}
```

### **Index:**
```javascript
db.api_keys.createIndex(
  { "user_id": 1, "provider": 1 },
  { unique: true }
)
```

## 🧪 Testing

### **Test 1: Sync từ file**
```powershell
# 1. Tạo key.txt
echo "sk-or-v1-test-key" > key.txt

# 2. Xóa key trong DB (nếu có)
python -c "from db import api_keys_col; api_keys_col().delete_many({})"

# 3. Login
# Key sẽ được load từ file và sync vào DB
```

### **Test 2: Sync từ environment**
```powershell
# 1. Xóa key.txt
rm key.txt

# 2. Set env var
$env:OPENROUTER_API_KEY="sk-or-v1-test-key"

# 3. Login
# Key sẽ được load từ env và sync vào DB
```

### **Test 3: Ưu tiên Database**
```powershell
# 1. Đã có key trong DB
# 2. Tạo key.txt với key khác
# 3. Login
# → Sẽ dùng key trong DB (không sync từ file)
```

### **Test 4: Auto-provision**
```powershell
# 1. Xóa tất cả keys
rm key.txt
$env:OPENROUTER_API_KEY=""

# 2. Set provisioning key
$env:OPENROUTER_PROVISIONING_KEY="sk-or-v1-provisioning-key"

# 3. Login
# → Tự động tạo runtime key mới
```

## 📝 Logs Reference

### **Successful Sync:**
```
[KeyManager] ===== Syncing API key for user 68e228e8 =====
[KeyManager] ✅ Loaded key from key.txt: ***************b465
[KeyManager] ✅ Saved key to database (source: key.txt): ***************b465
[KeyManager] ✅ Using key from: key.txt
[KeyManager] ✅ Key synced to database
[KeyManager] ===== Sync complete =====
```

### **Using Existing DB Key:**
```
[KeyManager] ===== Syncing API key for user 68e228e8 =====
[KeyManager] ✅ Loaded key from database: ***************b465
[KeyManager] ✅ Using key from: database
[KeyManager] ===== Sync complete =====
```

### **Auto-provision:**
```
[KeyManager] ⚠️ No API key found in database, file, or environment
[KeyManager] 🔄 Attempting auto-provision...
[KeyManager] 🔄 Auto-provisioning new key for user 68e228e8...
[KeyManager] ✅ Auto-provisioned new key: ***************a123
[KeyManager] ✅ Saved key to database (source: auto-provisioned): ***************a123
[KeyManager] ✅ Using key from: auto-provisioned
[KeyManager] ✅ Key synced to database
```

### **No Key Available:**
```
[KeyManager] ⚠️ No API key found in database, file, or environment
[KeyManager] 🔄 Attempting auto-provision...
[KeyManager] ⚠️ OPENROUTER_PROVISIONING_KEY not set, cannot auto-provision
[KeyManager] ❌ No API key available
```

## 🎯 Best Practices

1. **Production:** Sử dụng environment variables
2. **Development:** Sử dụng key.txt (gitignored)
3. **Auto-scaling:** Sử dụng provisioning key
4. **Security:** Rotate keys định kỳ
5. **Monitoring:** Check logs để verify sync

## 🔐 Security

- ✅ Keys được mask trong logs
- ✅ Keys không được commit vào Git (key.txt in .gitignore)
- ✅ Database keys nên được encrypt (TODO: implement encryption)
- ✅ Provisioning key phải được bảo mật tuyệt đối

## 🆘 Troubleshooting

### **Key không sync:**
- Check logs để xem lỗi
- Verify key format (phải bắt đầu với `sk-or-v1-`)
- Check file permissions

### **401 Unauthorized:**
- Key không hợp lệ hoặc hết hạn
- Lấy key mới từ https://openrouter.ai/keys

### **Key bị conflict:**
- Database key luôn được ưu tiên
- Xóa key trong DB nếu muốn sync từ file/env

---

**Hệ thống giờ đây HOÀN TOÀN TỰ ĐỘNG và THỐNG NHẤT! 🎉**
