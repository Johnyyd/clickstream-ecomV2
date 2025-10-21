# 📊 Comprehensive Clickstream Analytics Guide

## 🎯 Mục tiêu

Hệ thống phân tích clickstream toàn diện để:
- ✅ Tối ưu trải nghiệm khách hàng (UX)
- ✅ Đưa ra đề xuất sản phẩm cá nhân hóa
- ✅ Xây dựng chiến dịch marketing hiệu quả
- ✅ Phân tích Customer Journey
- ✅ Giảm bounce rate, tăng conversion rate
- ✅ Cung cấp insights cho SEO/Marketing/Product

---

## 🗂️ Dữ liệu & Collections

| Collection | Ý nghĩa | Liên kết |
|------------|---------|----------|
| **users** | Thông tin người dùng, gợi ý sản phẩm | `_id` ↔ `events.user_id`, `sessions.user_id` |
| **sessions** | Mỗi lần truy cập website | `session_id` ↔ `events.session_id` |
| **events** | Dòng click, hành động (pageview, add_to_cart, checkout, search) | Liên kết với `user_id`, `page`, `timestamp` |
| **products** | Sản phẩm chi tiết | `product_id` ↔ `carts.items.product_id` |
| **carts** | Giỏ hàng | Liên kết với `user_id`, `items.product_id` |

---

## ⚙️ Kiến trúc phân tích

### 1️⃣ Tầng Thu thập Dữ liệu (Data Collection)
- **Event Tracker**: Ghi nhận mọi hành động người dùng
- **MongoDB**: Lưu trữ dữ liệu thô
- **Kafka** (optional): Stream dữ liệu thời gian thực

### 2️⃣ Tầng Xử lý Dữ liệu (Data Processing)
- **Apache Spark**: Xử lý dữ liệu lớn
- **PySpark SQL**: Truy vấn và transform
- **ETL Pipeline**: Extract → Transform → Load

### 3️⃣ Tầng Học máy & Phân tích (ML & Analytics)
- **K-Means**: User Segmentation
- **Decision Tree**: Conversion Prediction
- **Logistic Regression**: Purchase Probability
- **ALS**: Product Recommendations
- **FP-Growth**: Pattern Mining

### 4️⃣ Tầng Hiển thị (Visualization)
- **Dashboard**: Power BI, Tableau, hoặc web-based
- **REST API**: FastAPI endpoints
- **Real-time Updates**: WebSocket (optional)

---

## 📊 Các Module Phân tích

### 1. **SEO & Traffic Source Analysis** 
📁 `spark_seo_analytics.py`

**Chức năng:**
- Phân tích nguồn traffic (organic, social, direct, paid)
- Landing page effectiveness
- Bounce rate by source
- Conversion rate by source
- Peak traffic hours

**Usage:**
```python
from spark_seo_analytics import analyze_traffic_sources

result = analyze_traffic_sources(username="alice")
print(result)
```

**Output:**
```json
{
  "algorithm": "SEO & Traffic Source Analysis",
  "traffic_by_source": [
    {"source": "organic_search", "sessions": 150, "events": 1200, "unique_users": 120},
    {"source": "social", "sessions": 80, "events": 600, "unique_users": 70}
  ],
  "landing_pages": [
    {"page": "/home", "sessions": 200, "avg_events": 6.5, "conversion_rate": 0.15, "bounce_rate": 0.25}
  ],
  "conversion_by_source": [...],
  "hourly_traffic": [...]
}
```

---

### 2. **Cart Abandonment Analysis**
📁 `spark_cart_analytics.py`

**Chức năng:**
- Cart abandonment rate
- Sản phẩm bị abandon nhiều nhất
- Giá trị giỏ hàng trung bình khi abandon
- So sánh giỏ completed vs abandoned

**Usage:**
```python
from spark_cart_analytics import analyze_cart_abandonment

result = analyze_cart_abandonment(username="bob")
```

**Output:**
```json
{
  "algorithm": "Cart Abandonment Analysis",
  "total_carts": 100,
  "abandoned_carts": 65,
  "abandonment_rate": 65.0,
  "avg_abandoned_value": 125.50,
  "most_abandoned_products": [
    {"product_name": "MacBook Air M3", "abandoned_count": 15}
  ]
}
```

---

### 3. **Cohort & Retention Analysis**
📁 `spark_retention_analytics.py`

**Chức năng:**
- Phân nhóm người dùng theo ngày đăng ký
- Retention rate (Week 1, Week 2, Month 1)
- User segments (Active, At Risk, Churned)
- Churn prediction

**Usage:**
```python
from spark_retention_analytics import analyze_cohort_retention

result = analyze_cohort_retention()
```

**Output:**
```json
{
  "algorithm": "Cohort & Retention Analysis",
  "cohorts": [
    {"cohort_date": "2025-01-15", "cohort_size": 50, "retention_week1": 75.0, "retention_month1": 45.0}
  ],
  "average_retention": {"week1": 70.5, "week2": 55.2, "month1": 42.3},
  "user_segments": [
    {"segment": "Active", "user_count": 500},
    {"segment": "At Risk", "user_count": 200},
    {"segment": "Churned", "user_count": 100}
  ]
}
```

---

### 4. **Customer Journey Path Analysis**
📁 `spark_journey_analytics.py`

**Chức năng:**
- Phân tích chuỗi hành động dẫn đến conversion
- Xác định drop-off points
- Path length analysis
- Common page sequences

**Usage:**
```python
from spark_journey_analytics import analyze_customer_journey

result = analyze_customer_journey()
```

**Output:**
```json
{
  "algorithm": "Customer Journey Path Analysis",
  "conversion_paths": [
    {"path": "/home -> category -> product -> cart -> checkout", "path_length": 5}
  ],
  "dropoff_points": [
    {"page": "cart", "dropout_count": 150, "avg_events_before": 4.2}
  ],
  "path_statistics": {
    "avg_path_length": 5.8,
    "median_path_length": 5.0
  },
  "common_sequences": [
    {"sequence": "product -> cart", "frequency": 450}
  ]
}
```

---

### 5. **Product Recommendation (ALS)**
📁 `spark_recommendation_als.py`

**Chức năng:**
- Collaborative Filtering using ALS
- Personalized product recommendations
- Implicit feedback (pageview=1, add_to_cart=3, purchase=5)
- Top-N recommendations per user

**Usage:**
```python
from spark_recommendation_als import ml_product_recommendations_als

result = ml_product_recommendations_als(username="alice", top_n=5)
```

**Output:**
```json
{
  "algorithm": "ALS Collaborative Filtering",
  "rmse": 0.85,
  "user": "alice",
  "recommendations": [
    {
      "product_name": "iPhone 15 Pro",
      "category": "phone",
      "price": 999.99,
      "predicted_rating": 4.5,
      "reason": "Predicted interest score: 4.5"
    }
  ]
}
```

---

### 6. **User Segmentation (K-Means)**
📁 `spark_ml.py`

**Chức năng:**
- Phân cụm người dùng theo hành vi
- Features: total_events, sessions_count, conversion_rate, cart_rate
- 3 clusters: Low/Medium/High value users

**Usage:**
```python
from spark_ml import ml_user_segmentation_kmeans

result = ml_user_segmentation_kmeans()
```

---

### 7. **Conversion Prediction (Decision Tree)**
📁 `spark_ml.py`

**Chức năng:**
- Dự đoán khả năng conversion
- Features: session_duration, page_views, product_views, cart_adds
- Feature importance analysis

**Usage:**
```python
from spark_ml import ml_conversion_prediction_tree

result = ml_conversion_prediction_tree()
```

---

### 8. **Purchase Prediction (Logistic Regression)**
📁 `spark_ml.py`

**Chức năng:**
- Dự đoán xác suất mua hàng
- Purchase probability score
- Feature coefficients analysis

**Usage:**
```python
from spark_ml import ml_purchase_prediction_logistic

result = ml_purchase_prediction_logistic()
```

---

### 9. **Pattern Mining (FP-Growth)**
📁 `spark_ml.py`

**Chức năng:**
- Tìm frequent patterns trong page navigation
- Association rules (if X then Y)
- Support và confidence metrics

**Usage:**
```python
from spark_ml import ml_pattern_mining_fpgrowth

result = ml_pattern_mining_fpgrowth()
```

---

## 🚀 Quick Start

### 1. Seed dữ liệu thực tế
```powershell
python seed_products.py
python seed_realistic_data.py --days 30 --user-count 1000 --sessions-per-user 5 --avg-events 7
```

### 2. Chạy phân tích cơ bản
```python
from spark_jobs import sessionize_and_counts

result = sessionize_and_counts(limit=10000)
print(result)
```

### 3. Chạy tất cả các phân tích
```python
from spark_seo_analytics import analyze_traffic_sources
from spark_cart_analytics import analyze_cart_abandonment
from spark_retention_analytics import analyze_cohort_retention
from spark_journey_analytics import analyze_customer_journey
from spark_recommendation_als import ml_product_recommendations_als

# SEO Analysis
seo_result = analyze_traffic_sources()

# Cart Analysis
cart_result = analyze_cart_abandonment()

# Retention Analysis
retention_result = analyze_cohort_retention()

# Journey Analysis
journey_result = analyze_customer_journey()

# Recommendations
recs_result = ml_product_recommendations_als(username="alice")
```

---

## 📈 Dashboard Metrics

### Traffic Overview
- Total Sessions, Users, Pageviews
- Sessions by Source
- Peak Traffic Hours
- Bounce Rate by Source

### Engagement Metrics
- Avg Session Duration
- Pages per Session
- Multi-page Session Rate
- Return Visitor Rate

### Conversion Funnel
- View → Product → Cart → Checkout → Purchase
- Conversion Rate at each step
- Drop-off Analysis

### User Segmentation
- Active Users (last 7 days)
- At Risk Users (8-30 days)
- Churned Users (>30 days)

### Product Insights
- Top Products by Views/Carts/Purchases
- Most Abandoned Products
- Cross-sell Opportunities
- Recommendation Impact

---

## 🧩 Ứng dụng Kết quả

### Marketing
- Tạo chiến dịch remarketing cho abandoned carts
- Tối ưu quảng cáo theo nguồn traffic hiệu quả nhất
- Personalized email campaigns

### SEO
- Tối ưu landing pages có bounce rate cao
- Cải thiện meta tags cho trang có traffic cao
- Internal linking strategy

### UX/UI
- Điều chỉnh giao diện tại drop-off points
- A/B testing cho conversion paths
- Mobile optimization

### Product Management
- Hiểu xu hướng sản phẩm đang được quan tâm
- Bundle products thường xem cùng nhau
- Pricing optimization

---

## 🔗 API Endpoints (FastAPI)

```python
# Run all analytics
POST /api/analytics/comprehensive
{
  "username": "alice",  # optional
  "limit": 10000,
  "modules": ["seo", "cart", "retention", "journey", "recommendations"]
}

# Specific analysis
GET /api/analytics/seo?username=alice
GET /api/analytics/cart-abandonment
GET /api/analytics/retention
GET /api/analytics/journey
GET /api/analytics/recommendations/alice
```

---

## 📚 Technical Stack

- **Backend**: Python 3.10+, FastAPI
- **Database**: MongoDB
- **Processing**: Apache Spark (PySpark)
- **ML**: Spark MLlib (ALS, K-Means, Decision Tree, Logistic Regression, FP-Growth)
- **Queue**: Apache Kafka (optional)
- **Visualization**: Power BI / Tableau / Custom Dashboard

---

## 💡 Best Practices

1. **Data Quality**: Loại bỏ noisy data trước khi phân tích
2. **Sampling**: Sử dụng limit cho dataset lớn
3. **Caching**: Cache Spark DataFrames cho multiple operations
4. **Incremental Processing**: Chỉ xử lý dữ liệu mới
5. **Monitoring**: Track analysis performance và errors
6. **Documentation**: Ghi chép insights và decisions

---

## 🐛 Troubleshooting

### Spark Out of Memory
```python
# Increase memory
spark = SparkSession.builder \
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.memory", "4g") \
    .getOrCreate()
```

### Slow Performance
- Reduce dataset size with `limit`
- Use `repartition()` for better parallelism
- Cache frequently accessed DataFrames
- Optimize SQL queries

### No Data Found
- Check data filters (flag.noisy, properties.source)
- Verify user exists
- Ensure events have required fields

---

## 📞 Support

For issues or questions:
- GitHub Issues
- Documentation: `README.md`, `ANALYSIS_FEATURES.md`
- Code examples: `tests/` directory

---

**Version**: 2.0  
**Last Updated**: 2025-01-21  
**Maintainer**: Clickstream Analytics Team
