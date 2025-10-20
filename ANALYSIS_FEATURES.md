# Tính năng phân tích mới - Analysis Features

## Tổng quan

Hệ thống đã được cập nhật với các tính năng phân tích linh hoạt và mạnh mẽ hơn:

### 1. **Phân tích toàn bộ Database** (Mặc định)
- Phân tích tất cả người dùng và toàn bộ dữ liệu trong MongoDB
- Cung cấp cái nhìn tổng quan về hành vi người dùng trên toàn hệ thống
- Giúp hiểu xu hướng chung và insights toàn cục

### 2. **Phân tích người dùng cụ thể** (Tùy chọn)
- Phân tích hành vi của một người dùng duy nhất
- Chỉ cần nhập **username** để phân tích
- Hữu ích cho việc cá nhân hóa và phân tích chi tiết

### 3. **Engine mặc định: Apache Spark**
- **Spark** là engine phân tích mặc định
- Xử lý hiệu quả với dataset lớn
- Tự động fallback về **Python** nếu Spark gặp lỗi

---

## Cách sử dụng trên Dashboard

### Bước 1: Đăng nhập
```
1. Truy cập /dashboard
2. Đăng nhập với username và password
```

### Bước 2: Chọn chế độ phân tích

Sau khi đăng nhập, bạn sẽ thấy 2 nút:

#### 📊 **All Users (Database)** - Mặc định
- Click nút này để phân tích toàn bộ database
- Phân tích tất cả người dùng và tất cả events
- Phù hợp cho báo cáo tổng quan

#### 👤 **Single User**
- Click nút này để phân tích một user cụ thể
- Nhập **username** vào ô input
- Click nút "Run Spark Analysis" để chạy

### Bước 3: Chạy phân tích

```
1. Chọn mode phân tích (All Users hoặc Single User)
2. Nếu chọn Single User, nhập username
3. Click "Run Spark Analysis"
4. Đợi kết quả hiển thị
```

---

## API Endpoints

### POST `/api/analyze`

Chạy phân tích với các tùy chọn:

#### Phân tích toàn bộ database:
```json
{
  "params": {
    "analysis_target": "all",
    "use_spark": true
  }
}
```

#### Phân tích user cụ thể:
```json
{
  "params": {
    "analysis_target": "username:john_doe",
    "use_spark": true
  }
}
```

#### Phân tích user hiện tại (mặc định):
```json
{
  "params": {
    "use_spark": true
  }
}
```

---

## Cấu hình

### Environment Variables

```bash
# Sử dụng Spark làm engine mặc định (đã set mặc định = true)
USE_SPARK=true

# Nếu muốn dùng Python làm mặc định
USE_SPARK=false
```

### Trong code

File `analysis.py`:
```python
# Default to TRUE - use Spark by default, fallback to Python on error
USE_SPARK = os.environ.get('USE_SPARK', 'true').lower() == 'true'
```

---

## Luồng xử lý

```
User clicks "Run Analysis"
    ↓
Dashboard.js xác định target:
  - 'all' → Toàn bộ database
  - 'username:xxx' → User cụ thể
  - None → User hiện tại
    ↓
API /api/analyze nhận request
    ↓
run_analysis(user_id, params)
  - user_id = None → Analyze ALL
  - user_id = ObjectId → Analyze specific user
    ↓
Try Spark Analysis
    ↓ (nếu lỗi)
Fallback to Python Analysis
    ↓
Save results to MongoDB.analyses
    ↓
Return analysis ID to frontend
    ↓
Frontend hiển thị kết quả
```

---

## Tính năng bổ sung

### Auto-Analyze
- Tự động chạy phân tích định kỳ (mỗi 60 giây)
- Sử dụng analysis target hiện tại
- Skip LLM để tăng tốc độ

### Real-time Metrics
- Cập nhật metrics mỗi 10 giây
- Hiển thị biểu đồ realtime
- Giám sát events theo thời gian thực

---

## Đồng bộ dữ liệu

### Dashboard ↔ MongoDB

Tất cả dữ liệu trên dashboard luôn được đồng bộ với MongoDB:

1. **Events**: Mọi event được lưu ngay vào `events` collection
2. **Analyses**: Kết quả phân tích lưu vào `analyses` collection
3. **Sessions**: Session tracking trong `sessions` collection
4. **Real-time updates**: Polling API mỗi 10 giây

### Đảm bảo consistency

- Sử dụng MongoDB ObjectId cho user_id
- Timestamp được chuẩn hóa về UTC
- Indexes được tối ưu cho queries

---

## Troubleshooting

### Spark không hoạt động?
- Kiểm tra Spark đã được cài đặt đúng
- Xem logs console để biết lỗi cụ thể
- Hệ thống sẽ tự động fallback về Python

### Không tìm thấy username?
- Đảm bảo username nhập chính xác
- Kiểm tra user tồn tại trong database
- Error message sẽ hiển thị nếu user không tồn tại

### Analysis chậm?
- Với dataset lớn, Spark analysis có thể mất vài phút
- Có thể giới hạn số events bằng tham số `limit`
- Sử dụng Auto-Analyze với skip_llm để tăng tốc

---

## Ví dụ sử dụng

### Case 1: Marketing Team - Phân tích toàn bộ
```
Mục đích: Hiểu behavior của tất cả users
Cách làm:
1. Login vào dashboard
2. Giữ mode "All Users (Database)" (mặc định)
3. Click "Run Spark Analysis"
4. Xem insights tổng quan về conversion, bounce rate, top pages
```

### Case 2: Customer Success - Phân tích VIP customer
```
Mục đích: Phân tích chi tiết behavior của customer quan trọng
Cách làm:
1. Login vào dashboard
2. Click "Single User"
3. Nhập username: "vip_customer_123"
4. Click "Run Spark Analysis"
5. Xem insights chi tiết và personalized recommendations
```

### Case 3: Developer - Debug user issues
```
Mục đích: Debug vấn đề của user cụ thể
Cách làm:
1. Login vào dashboard
2. Click "Single User"
3. Nhập username của user gặp vấn đề
4. Analyze để xem event timeline và behavior
5. Identify issues trong funnel
```

---

## Best Practices

1. **Phân tích định kỳ**: Dùng "All Users" hàng ngày để track metrics
2. **Phân tích sâu**: Dùng "Single User" khi cần investigate
3. **Auto-Analyze**: Bật để giữ dashboard luôn cập nhật
4. **Spark vs Python**: Tin tưởng vào auto-fallback
5. **LLM Insights**: Tắt skip_llm khi cần insights chi tiết

---

## Technical Details

### Database Schema

```javascript
// analyses collection
{
  _id: ObjectId,
  user_id: ObjectId | null,  // null = analyze all users
  created_at: ISODate,
  parameters: {
    analysis_target: "all" | "username:xxx" | undefined,
    use_spark: true,
    limit: null
  },
  status: "done" | "failed",
  spark_summary: { ... },
  detailed_metrics: { ... },
  insights: { ... }
}
```

### Performance

- **Spark**: Xử lý 1M+ events trong < 5 phút
- **Python**: Phù hợp với < 100K events
- **Auto-fallback**: Không downtime khi Spark fail

---

## Changelog

### Version 2.0 - Analysis Features Update

#### Added
- ✅ Phân tích toàn bộ database (analysis_target: "all")
- ✅ Phân tích theo username (analysis_target: "username:xxx")
- ✅ Spark làm engine mặc định (USE_SPARK=true)
- ✅ UI controls cho analysis mode selection
- ✅ Auto-analyze với target support
- ✅ Enhanced error handling và fallback

#### Changed
- 🔄 USE_SPARK default: false → true
- 🔄 run_analysis() hỗ trợ user_id = None
- 🔄 API endpoint /analyze với analysis_target param

#### Fixed
- 🐛 ObjectId handling khi user_id = None
- 🐛 Dashboard sync với MongoDB
- 🐛 Fallback mechanism từ Spark sang Python

---

## Support

Nếu gặp vấn đề:
1. Check console logs
2. Verify MongoDB connection
3. Test với Python mode trước
4. Contact dev team với error details
