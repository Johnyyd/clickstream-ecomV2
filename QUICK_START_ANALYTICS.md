# 🚀 Quick Start - Comprehensive Analytics

## 📋 Prerequisites

1. **MongoDB running** on `localhost:27017`
2. **Python 3.10+** with virtual environment
3. **Java 17+** for Apache Spark
4. **Seeded data** (products + events)

---

## ⚙️ Setup

### 1. Install dependencies
```powershell
cd c:\LUUDULIEU\CODE\github\clickstream-ecomV2
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Set environment variables
```powershell
$env:MONGO_URI = "mongodb://localhost:27017"
$env:MONGO_DB = "clickstream"
$env:JAVA_HOME = "C:\LUUDULIEU\APP\JDK\jdk-17.0.12"
```

### 3. Seed data (if needed)
```powershell
# Seed products first
python seed_products.py

# Seed realistic user behavior
python seed_realistic_data.py --days 30 --user-count 1000 --sessions-per-user 5 --avg-events 7
```

---

## 🧪 Test Analytics Modules

### Option 1: Test Individual Modules
```powershell
python test_comprehensive_analytics.py --mode individual
```

This will test each analytics module separately:
- ✅ SEO & Traffic Source Analysis
- ✅ Cart Abandonment Analysis
- ✅ Cohort & Retention Analysis
- ✅ Customer Journey Path Analysis
- ✅ Product Recommendations (ALS)
- ✅ User Segmentation (K-Means)
- ✅ Conversion Prediction (Decision Tree)
- ✅ Purchase Probability (Logistic Regression)
- ✅ Pattern Mining (FP-Growth)

### Option 2: Test with Orchestrator
```powershell
python test_comprehensive_analytics.py --mode orchestrator
```

This runs all modules together with a unified interface.

### Option 3: Test All
```powershell
python test_comprehensive_analytics.py --mode all
```

---

## 🎯 Run Analytics via CLI

### Run All Analytics for All Users
```powershell
python analytics_orchestrator.py
```

### Run for Specific User
```powershell
python analytics_orchestrator.py --username alice
```

### Export Results to JSON
```powershell
python analytics_orchestrator.py --export my_results.json
```

---

## 🌐 Run Analytics via API

### 1. Start the FastAPI server
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Test API endpoints

#### Health Check
```bash
curl http://localhost:8000/api/analytics/health
```

#### SEO Analysis
```bash
curl http://localhost:8000/api/analytics/seo
curl "http://localhost:8000/api/analytics/seo?username=alice"
```

#### Cart Abandonment
```bash
curl http://localhost:8000/api/analytics/cart-abandonment
```

#### Cohort Retention
```bash
curl http://localhost:8000/api/analytics/retention
```

#### Customer Journey
```bash
curl http://localhost:8000/api/analytics/customer-journey
```

#### Product Recommendations
```bash
curl http://localhost:8000/api/analytics/recommendations/alice
```

#### User Segmentation
```bash
curl http://localhost:8000/api/analytics/user-segmentation
```

#### Conversion Prediction
```bash
curl http://localhost:8000/api/analytics/conversion-prediction
```

#### Purchase Probability
```bash
curl http://localhost:8000/api/analytics/purchase-probability
```

#### Pattern Mining
```bash
curl http://localhost:8000/api/analytics/pattern-mining
```

#### **Comprehensive Analysis (All Modules)**
```bash
curl -X POST http://localhost:8000/api/analytics/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "username": null,
    "limit": null,
    "modules": ["all"]
  }'
```

#### **Specific Modules Only**
```bash
curl -X POST http://localhost:8000/api/analytics/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "modules": ["seo", "cart", "recommendations"]
  }'
```

---

## 📊 View Results

### Interactive API Documentation
Open in browser: **http://localhost:8000/docs**

This provides an interactive Swagger UI to test all endpoints.

### JSON Export
Results are automatically exported when using the CLI orchestrator:
```powershell
python analytics_orchestrator.py --export results.json
cat results.json | jq .
```

---

## 🔍 Example Workflows

### Workflow 1: Marketing Campaign Analysis
```powershell
# 1. Analyze traffic sources
curl http://localhost:8000/api/analytics/seo > seo_results.json

# 2. Identify high-value user segments
curl http://localhost:8000/api/analytics/user-segmentation > segments.json

# 3. Get recommendations for top users
curl http://localhost:8000/api/analytics/recommendations/alice > alice_recs.json
```

### Workflow 2: Conversion Optimization
```powershell
# 1. Analyze customer journey
curl http://localhost:8000/api/analytics/customer-journey > journey.json

# 2. Identify drop-off points
# Check journey.json for dropoff_points

# 3. Predict conversion likelihood
curl http://localhost:8000/api/analytics/conversion-prediction > conversion.json
```

### Workflow 3: Cart Recovery Campaign
```powershell
# 1. Analyze cart abandonment
curl http://localhost:8000/api/analytics/cart-abandonment > carts.json

# 2. Get most abandoned products
# Check carts.json for most_abandoned_products

# 3. Create targeted remarketing list
# Use user_ids from abandoned carts
```

### Workflow 4: Retention Improvement
```powershell
# 1. Analyze cohort retention
curl http://localhost:8000/api/analytics/retention > retention.json

# 2. Identify at-risk users
# Check retention.json for user_segments

# 3. Generate personalized recommendations
curl http://localhost:8000/api/analytics/recommendations/bob > bob_recs.json
```

---

## 🐛 Troubleshooting

### Issue: "No data available"
**Solution:** Seed more data
```powershell
python seed_realistic_data.py --days 30 --user-count 500 --sessions-per-user 10
```

### Issue: "Need at least X interactions for ALS"
**Solution:** The ALS recommendation system needs sufficient product interaction data. Seed more product views and purchases:
```powershell
python seed_realistic_data.py --days 30 --user-count 200 --avg-events 10
```

### Issue: Spark out of memory
**Solution:** Increase Spark memory in the analytics modules:
```python
# Edit spark_*_analytics.py files
.config("spark.driver.memory", "4g")
.config("spark.executor.memory", "4g")
```

### Issue: Slow performance
**Solution:** Use limit parameter to process fewer events:
```bash
curl -X POST http://localhost:8000/api/analytics/comprehensive \
  -H "Content-Type: application/json" \
  -d '{"limit": 10000}'
```

### Issue: Java not found
**Solution:** Set JAVA_HOME environment variable:
```powershell
$env:JAVA_HOME = "C:\Path\To\JDK\jdk-17.0.12"
```

---

## 📈 Performance Tips

1. **Use sampling**: Add `?limit=10000` to API calls for faster results
2. **Cache Spark DataFrames**: Modules already use caching for repeated operations
3. **Run during off-peak**: Schedule heavy analytics during low-traffic periods
4. **Incremental processing**: Process only new data since last run
5. **Parallel execution**: Run independent modules in parallel

---

## 📚 Additional Resources

- **Full Documentation**: `COMPREHENSIVE_ANALYTICS_GUIDE.md`
- **API Reference**: http://localhost:8000/docs
- **Code Examples**: `test_comprehensive_analytics.py`
- **Architecture**: See section "Kiến trúc phân tích" in guide

---

## 🎓 Next Steps

1. ✅ Run test suite to verify all modules work
2. ✅ Explore API documentation at `/docs`
3. ✅ Run comprehensive analysis via orchestrator
4. ✅ Integrate insights into your dashboard
5. ✅ Schedule periodic analytics runs
6. ✅ Set up monitoring and alerting

---

**Happy Analyzing! 🚀📊**
