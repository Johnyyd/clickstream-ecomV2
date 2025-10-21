# Quick Test - ML Features

## 🚀 Test ngay trong 5 phút

### 1. Start server
```bash
uvicorn app.main:app --reload
```

### 2. Login
```
URL: http://localhost:8000/dashboard
Username: customer001
Password: customer001123
```

### 3. Test Simulate Events mới (100 events realistic)
```
1. Click "Simulate Events (100)"
2. Chờ ~10-20 giây
3. Check output: "15 realistic events ingested (power_buyer persona)"
   - Số events thay đổi tùy persona (3-15 events)
   - Persona random: bouncer, browser, shopper, power_buyer, returning
```

### 4. Test ML Algorithms

#### Option A: Nếu có data sẵn (>100 users)
```
Click từng button:
✅ K-Means Clustering → Results in ~2s
✅ Decision Tree → Results in ~3s
✅ FP-Growth Patterns → Results in ~5s
✅ Logistic Regression → Results in ~3s
```

#### Option B: Nếu data ít, seed trước
```bash
.venv\Scripts\python.exe seed_realistic_data.py --user-count 100 --days 3 --sessions-per-user 3 --avg-events 7
```

### 5. Check results
```
ML results hiển thị ở đầu page với:
- 🔵 Purple border
- 📊 Metric cards
- 📈 Charts & tables
- 🎯 Insights
```

---

## 📊 Expected Results

### K-Means Clustering:
```
🤖 K-Means Clustering

Cluster Analysis
👥 100 Total Users
🎯 3 Clusters
📊 0.6234 Silhouette Score

Cluster Characteristics:
🔵 Low Value
  Users: 35
  Avg Events: 45.2
  Conversion: 5.23%
  Cart Rate: 12.34%

🟢 Medium Value
  ...

🟡 High Value
  ...
```

### Decision Tree:
```
🤖 Decision Tree

Conversion Prediction Model
🎯 0.7856 AUC Score
🌳 5 Tree Depth
📦 245 Training Samples

Feature Importance:
cart_adds     ████████████ 0.4523
product_views ████████ 0.3012
duration      █████ 0.1789
page_views    ███ 0.0676

Sample Predictions:
Session        | Actual       | Predicted    | Confidence
6a3e5b...      | ✅ Purchase  | ✅ Purchase  | 87.3%
```

### FP-Growth:
```
🤖 FP-Growth Pattern Mining

Frequent Navigation Patterns
📊 450 Sessions Analyzed
🔍 87 Patterns Found
📈 45 Association Rules

Top Frequent Patterns:
/home → /search → /product
  52 sessions | Support: 11.6%

/category → /product → /cart
  38 sessions | Support: 8.4%

Top Association Rules:
/search, /product ⇒ /cart
  Confidence: 67.5% | Lift: 2.34
```

### Logistic Regression:
```
🤖 Logistic Regression

Purchase Probability Prediction
🎯 0.8123 AUC Score
📦 315 Training Samples
🧪 135 Test Samples

Feature Coefficients:
cart_adds        +0.8234 (green)
has_history      +0.6123
product_views    +0.3456
duration         +0.1234
page_views       -0.0543 (red)

Intercept: -2.3456

Sample Predictions:
Session    | Actual       | Predicted    | Purchase Prob
7b4f9c...  | ✅ Purchase  | ✅ Purchase  | ████████ 82.3%
```

---

## ✅ Checklist

### UI Changes:
- [ ] Button text: "Simulate Events (100)" ✅
- [ ] ML buttons section below Spark Analysis ✅
- [ ] 4 purple gradient buttons ✅

### Simulate Events:
- [ ] Generates 100 events (varies by persona) ✅
- [ ] Shows persona in output ✅
- [ ] Realistic pages & properties ✅
- [ ] Entry points: home/search/social ✅

### ML Algorithms:
- [ ] K-Means button works ✅
- [ ] Decision Tree button works ✅
- [ ] FP-Growth button works ✅
- [ ] Logistic Regression button works ✅

### Results Display:
- [ ] Purple border box at top ✅
- [ ] Metric cards with icons ✅
- [ ] Charts/bars/tables ✅
- [ ] Responsive layout ✅

---

## 🐛 Quick Fixes

### "Need at least X sessions"
```bash
# Generate more data
.venv\Scripts\python.exe seed_realistic_data.py --user-count 200 --days 5 --sessions-per-user 4 --avg-events 8
```

### "No module named pyspark.ml"
```bash
pip install pyspark
```

### Results not showing
```
Hard refresh: Ctrl + Shift + R
```

### Slow ML execution
```
Normal - algorithms take 2-7 seconds
Check output for progress
```

---

## 🎉 Done!

Nếu tất cả test pass:
- ✅ Simulate Events đã upgrade 10 → 100
- ✅ 4 ML algorithms hoạt động
- ✅ Results hiển thị đẹp
- ✅ Ready for production!

🚀 **Enjoy your new ML-powered dashboard!**
