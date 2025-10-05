# API Key Management - Documentation

## Tổng quan
Server đã được tích hợp đầy đủ các chức năng quản lý OpenRouter API key với validation, logging và bảo mật.

## Endpoints

### 1. Lưu API Key (POST)
**Endpoint:** `POST /api/openrouter/key`

**Headers:**
- `Authorization`: Bearer token từ login
- `Content-Type`: application/json

**Request Body:**
```json
{
  "api_key": "sk-or-v1-xxxxxxxxxxxxx"
}
```

**Response Success (200):**
```json
{
  "status": "ok",
  "message": "API key saved successfully"
}
```

**Response Error (400):**
```json
{
  "error": "Invalid API key format. OpenRouter keys should start with 'sk-or-'"
}
```

**Tính năng:**
- ✅ Validate format API key (phải bắt đầu với `sk-or-`)
- ✅ Lưu vào MongoDB với timestamp
- ✅ Log với masked key (chỉ hiện 4 ký tự cuối)
- ✅ Upsert (tạo mới hoặc cập nhật)

---

### 2. Kiểm tra API Key (GET)
**Endpoint:** `GET /api/openrouter/key`

**Headers:**
- `Authorization`: Bearer token từ login

**Response Success (200):**
```json
{
  "exists": true,
  "provider": "openrouter",
  "masked_key": "***************b465",
  "updated_at": "2025-10-05T08:42:35.123Z"
}
```

**Response No Key (200):**
```json
{
  "exists": false,
  "provider": "openrouter"
}
```

**Tính năng:**
- ✅ Kiểm tra sự tồn tại của API key
- ✅ Trả về masked key (bảo mật)
- ✅ Hiển thị thời gian cập nhật cuối

---

### 3. Xóa API Key (DELETE)
**Endpoint:** `DELETE /api/openrouter/key`

**Headers:**
- `Authorization`: Bearer token từ login

**Response Success (200):**
```json
{
  "status": "ok",
  "message": "API key deleted successfully"
}
```

**Response Not Found (404):**
```json
{
  "error": "No API key found to delete"
}
```

**Tính năng:**
- ✅ Xóa API key khỏi database
- ✅ Log thao tác xóa
- ✅ Kiểm tra quyền user

---

### 4. Provision Runtime Key (POST)
**Endpoint:** `POST /api/openrouter/provision`

**Headers:**
- `Authorization`: Bearer token từ login
- `Content-Type`: application/json

**Request Body (Optional):**
```json
{
  "name": "my-runtime-key",
  "limit": 100.0
}
```

**Response Success (200):**
```json
{
  "status": "ok",
  "meta": {
    "key_hash": "xxxxx",
    "name": "my-runtime-key",
    "limit": 100.0
  },
  "message": "Runtime key provisioned successfully"
}
```

**Yêu cầu:**
- ⚠️ Cần set biến môi trường `OPENROUTER_PROVISIONING_KEY`
- ⚠️ Provisioning key phải có quyền tạo runtime keys

**Tính năng:**
- ✅ Tự động tạo runtime key qua OpenRouter API
- ✅ Lưu key mới vào database
- ✅ Log với masked key
- ✅ Tự động đặt tên nếu không cung cấp

---

## Cách sử dụng

### Từ Dashboard (Frontend)
```javascript
// Lưu API key
const saveKey = async (apiKey) => {
  const resp = await fetch('/api/openrouter/key', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token
    },
    body: JSON.stringify({ api_key: apiKey })
  });
  return await resp.json();
};

// Kiểm tra API key
const checkKey = async () => {
  const resp = await fetch('/api/openrouter/key', {
    headers: { 'Authorization': token }
  });
  return await resp.json();
};

// Xóa API key
const deleteKey = async () => {
  const resp = await fetch('/api/openrouter/key', {
    method: 'DELETE',
    headers: { 'Authorization': token }
  });
  return await resp.json();
};
```

### Từ Python Script
```python
import requests

# Login trước
login_resp = requests.post('http://localhost:8000/api/login', 
    json={'username': 'admin', 'password': 'password'})
token = login_resp.json()['token']

# Lưu API key
save_resp = requests.post('http://localhost:8000/api/openrouter/key',
    headers={'Authorization': token},
    json={'api_key': 'sk-or-v1-xxxxx'})
print(save_resp.json())
```

---

## Bảo mật

### ✅ Đã implement:
1. **Authentication**: Tất cả endpoints yêu cầu token hợp lệ
2. **Validation**: Kiểm tra format API key
3. **Logging**: Log với masked key (chỉ hiện 4 ký tự cuối)
4. **Error Handling**: Xử lý lỗi đầy đủ với message rõ ràng
5. **CORS**: Hỗ trợ cross-origin requests

### ⚠️ Lưu ý:
- API key được lưu trong MongoDB với field `key_encrypted`
- Trong production, nên mã hóa API key trước khi lưu vào DB
- Provisioning key (`OPENROUTER_PROVISIONING_KEY`) phải được bảo mật tuyệt đối

---

## Testing

### Test với curl:
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.token')

# Lưu API key
curl -X POST http://localhost:8000/api/openrouter/key \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"sk-or-v1-xxxxx"}'

# Kiểm tra API key
curl -X GET http://localhost:8000/api/openrouter/key \
  -H "Authorization: $TOKEN"

# Xóa API key
curl -X DELETE http://localhost:8000/api/openrouter/key \
  -H "Authorization: $TOKEN"
```

---

## Database Schema

### Collection: `api_keys`
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "provider": "openrouter",
  "key_encrypted": "sk-or-v1-xxxxx",
  "created_at": ISODate("2025-10-05T08:00:00Z"),
  "updated_at": ISODate("2025-10-05T08:42:35Z")
}
```

### Index:
```javascript
db.api_keys.createIndex({ "user_id": 1, "provider": 1 }, { unique: true })
```

---

## Changelog

### v2.0 (2025-10-05)
- ✅ Thêm validation format API key
- ✅ Thêm endpoint DELETE để xóa key
- ✅ Thêm endpoint POST provision runtime key
- ✅ Cải thiện logging với masked key
- ✅ Thêm message rõ ràng cho response
- ✅ Fix lỗi endpoint provision (di chuyển từ GET sang POST)
- ✅ Hỗ trợ CORS với DELETE method
