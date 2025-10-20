# Hướng dẫn sử dụng tính năng phân tích đơn giản

## 🎯 Cách hoạt động

Khi bạn nhấn **"Run Spark Analysis"**, hệ thống sẽ tự động:

### 1️⃣ Nếu KHÔNG nhập username
```
➜ Phân tích TOÀN BỘ dữ liệu từ database
➜ Bao gồm tất cả users
➜ Cung cấp insights tổng quan
```

### 2️⃣ Nếu CÓ nhập username
```
➜ Phân tích CHỈ user đó
➜ Data cụ thể của user
➜ Insights cá nhân hóa
```

---

## 📖 Hướng dẫn sử dụng

### Bước 1: Đăng nhập
```
1. Vào /dashboard
2. Nhập username và password
3. Click "Login"
```

### Bước 2: Chọn loại phân tích

#### ✅ Phân tích toàn bộ (Mặc định)
```
1. ĐỂ TRỐNG ô "Username (Optional)"
2. Click "Run Spark Analysis"
3. Xem kết quả toàn bộ database
```

**Ví dụ:**
```
Username field: [____________]  (trống)
Click "Run Spark Analysis"
→ Analyzing ALL USERS
```

#### ✅ Phân tích user cụ thể
```
1. NHẬP username vào ô "Username (Optional)"
   Ví dụ: "customer001"
2. Click "Run Spark Analysis"
3. Xem kết quả của user đó
```

**Ví dụ:**
```
Username field: [customer001]
Click "Run Spark Analysis"
→ Analyzing user: customer001
```

---

## 💡 Use Cases

### Case 1: Marketing Team - Dashboard tổng quan
```
Mục đích: Xem metrics của toàn bộ hệ thống
Cách làm:
  1. Login
  2. Để trống username field
  3. Click "Run Spark Analysis"
  4. Xem insights tổng quan
```

### Case 2: Customer Success - Check VIP customer
```
Mục đích: Xem behavior của customer quan trọng
Cách làm:
  1. Login
  2. Nhập username: "vip_customer_123"
  3. Click "Run Spark Analysis"
  4. Xem insights cá nhân
```

### Case 3: Developer - Debug user issue
```
Mục đích: Debug vấn đề của user cụ thể
Cách làm:
  1. Login
  2. Nhập username của user gặp issue
  3. Click "Run Spark Analysis"
  4. Analyze event timeline và behavior
```

---

## 🎨 Giao diện

```
┌─────────────────────────────────────────┐
│  Username (Optional)                    │
│  Leave empty to analyze all users       │
│  ┌─────────────────────────────────┐   │
│  │ Enter username...               │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘

       [ Run Spark Analysis ]
```

### Trạng thái khi chạy:

**1. Phân tích tất cả:**
```
Running Spark analysis for ALL USERS (entire database)...
```

**2. Phân tích user cụ thể:**
```
Running Spark analysis for user: customer001...
```

---

## ⚙️ Technical Details

### API Request khi không nhập username:
```json
POST /api/analyze
{
  "params": {
    "analysis_target": "all",
    "use_spark": true
  }
}
```

### API Request khi nhập username:
```json
POST /api/analyze
{
  "params": {
    "analysis_target": "username:customer001",
    "use_spark": true
  }
}
```

### Backend xử lý:
```python
# Trong analysis.py
def run_analysis(user_id, params):
    if user_id is None:
        # Analyze ALL users
        print("Starting Analysis for ALL USERS")
    else:
        # Analyze specific user
        print(f"Starting Analysis for User {user_id}")
```

---

## 🔧 Auto-Analyze

Auto-Analyze cũng tuân theo logic tương tự:

```
1. Click "Start Auto-Analyze"
2. Nếu username field trống → Auto-analyze ALL
3. Nếu có username → Auto-analyze user đó
4. Chạy mỗi 60 giây
```

---

## ✅ Advantages

### 1. Đơn giản
- Không cần chọn mode
- Không cần click nhiều buttons
- Chỉ cần nhập hoặc để trống

### 2. Intuitive
- Logic rõ ràng: có username = single user, không có = all
- Hint text giải thích rõ ràng
- Không gây confuse

### 3. Flexible
- Dễ dàng switch giữa all và single
- Chỉ cần xóa/nhập username
- Không cần reset gì cả

---

## 🐛 Error Handling

### Username không tồn tại:
```
Input: "ghost_user"
Error: User 'ghost_user' not found
```

### Spark lỗi:
```
Spark analysis failed
→ Auto fallback to Python
→ Analysis continues successfully
```

---

## 📊 Data Flow

```
User clicks "Run Spark Analysis"
    ↓
Check username field
    ↓
┌─────────────────┬───────────────────┐
│ Empty           │ Has value         │
│ analysis_target │ analysis_target   │
│ = "all"         │ = "username:xxx"  │
└────────┬────────┴──────────┬────────┘
         │                   │
         ↓                   ↓
    Analyze ALL         Analyze USER
         │                   │
         └───────┬───────────┘
                 ↓
         Save to MongoDB
                 ↓
         Display Results
```

---

## 🎯 Best Practices

### 1. Daily Monitoring
```
- Để trống username
- Bật Auto-Analyze
- Monitor dashboard mỗi ngày
```

### 2. User Investigation
```
- Nhập username khi cần
- Check specific behavior
- Debug issues
```

### 3. Performance
```
- Toàn bộ DB: Dùng Spark (auto)
- Single user: Python cũng OK
- Trust auto-fallback
```

---

## 🚀 Quick Start

### 30-second guide:
```bash
1. Login vào /dashboard
2. Để trống username field
3. Click "Run Spark Analysis"
4. Wait ~30s (Spark startup)
5. See results!

# Muốn analyze user?
6. Nhập username
7. Click "Run Spark Analysis" lại
8. Done!
```

---

## 📝 Summary

| Scenario | Username Field | Result |
|----------|----------------|---------|
| Overview | Empty (trống) | Analyze ALL users |
| Specific user | "customer001" | Analyze customer001 only |
| Debug | "user_xyz" | Analyze user_xyz only |
| Auto-Analyze | Empty | Auto ALL every 60s |
| Auto-Analyze | "vip_user" | Auto vip_user every 60s |

---

## ❓ FAQ

**Q: Làm sao để phân tích toàn bộ?**
A: Để trống username field và click "Run Spark Analysis"

**Q: Làm sao để phân tích 1 user?**
A: Nhập username vào field và click "Run Spark Analysis"

**Q: Có cần click button "All Users" không?**
A: KHÔNG! Không còn button đó nữa, chỉ cần check username field

**Q: Auto-Analyze hoạt động thế nào?**
A: Nó sẽ dùng username hiện tại trong field. Trống = all, có = user đó

**Q: Username có phân biệt hoa thường không?**
A: CÓ. "John" ≠ "john"

**Q: Spark chậm quá?**
A: Lần đầu ~30s do startup. Lần sau nhanh hơn. Hoặc dùng Python mode

---

## 🎉 That's it!

Cực kỳ đơn giản:
- **Không nhập** → Phân tích ALL
- **Có nhập** → Phân tích USER đó

No more confusion! 🚀
