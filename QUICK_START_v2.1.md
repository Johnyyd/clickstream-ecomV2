# Quick Start Guide v2.1

## 🚀 Cách sử dụng ngay

### 1. Clear old data (nếu cần test từ đầu)
```bash
mongo clickstream_db --eval "db.events.deleteMany({}); db.sessions.deleteMany({}); db.analyses.deleteMany({});"
```

### 2. Generate dữ liệu realistic mới
```bash
.venv\Scripts\python.exe seed_realistic_data.py --user-count 100 --days 7 --sessions-per-user 4 --avg-events 7 --seed-products
```

**Chờ ~2-5 phút tùy vào số lượng users**

Output sẽ hiển thị personas:
```
User abc123: bouncer
User def456: browser
User ghi789: shopper
User jkl012: power_buyer
...
✅ Estimated events inserted: ~19600
✅ Sessions upserted: 2800
```

### 3. Start server
```bash
uvicorn app.main:app --reload
```

### 4. Hard refresh browser
```
Ctrl + Shift + R (Windows)
Cmd + Shift + R (Mac)
```

### 5. Login & Test
```
1. Go to http://localhost:8000/dashboard
2. Login: customer001 / customer001123
3. Wait 10s → Real-time Metrics hiển thị
4. Click "Run Spark Analysis" (leave username empty)
5. Wait ~1-2 min → Analysis results
```

---

## ✅ Checklist

### Real-time Metrics (Should see immediately):
- [ ] Header: "Real-time Metrics (last 5 min)"
- [ ] Events (5m): > 0
- [ ] Top Event: pageview with count
- [ ] Top Page: /home with count
- [ ] Line chart có data
- [ ] Auto-updates mỗi 10s

### Time Analysis (After running analysis):
- [ ] Peak Hour card (e.g., "20:00")
- [ ] Peak Day card (e.g., "Friday")
- [ ] Hourly Distribution: 24 bars (0-23)
- [ ] Daily Distribution: 7 bars (Mon-Sun)
- [ ] Bars có chiều cao khác nhau
- [ ] Hover effect hoạt động

### Data Quality:
- [ ] Bounce Rate: 10-20% (không phải 0%)
- [ ] Conversion funnel realistic
- [ ] Events spread across 24 hours
- [ ] Multiple user behaviors visible

---

## 🎯 Các tính năng mới

### 1. Dữ liệu Realistic
- **5 User Personas:** Bouncer, Browser, Shopper, Power Buyer, Returning Customer
- **24/7 Traffic:** Natural peaks at 9-11 AM and 7-9 PM
- **Diverse Behavior:** Different conversion rates, session lengths
- **Entry Points:** 60% home, 25% search, 15% social

### 2. Time Analysis Display
- **Peak Metrics:** Hour and Day
- **Hourly Chart:** 24-hour distribution
- **Daily Chart:** Weekly distribution
- **Beautiful UI:** Gradient bars with hover effects

### 3. Real-time Metrics
- **5-minute window** (was 60 min)
- **10-second polling**
- **Live data** (not static 0)

---

## 🐛 Troubleshooting

### Real-time Metrics shows 0:
```bash
# Simulate some events
1. Login to dashboard
2. Click "Simulate Events (10)"
3. Wait 10 seconds
4. Metrics should update
```

### Time Analysis empty:
```bash
# Need to run analysis first
1. Click "Run Spark Analysis"
2. Wait for completion
3. Scroll down to see Time Analysis
```

### Charts not showing:
```bash
# Hard refresh to clear cache
Ctrl + Shift + R

# Or clear browser cache
F12 → Application → Clear storage
```

### No diversity in data:
```bash
# Re-seed with new script
1. Delete old data
2. Run seed_realistic_data.py again
3. Check output shows different personas
```

---

## 📊 Expected Results

### Analysis Summary:
```
Total Events: 15,000-25,000
Total Sessions: 2,000-4,000
Unique Users: 100
Avg. Session Duration: 8-15 mins
Bounce Rate: 10-20%
```

### Time Analysis:
```
Peak Hour: 20:00 (or 9:00, 10:00, 21:00)
Peak Day: Friday (or Monday, Wednesday)
Hourly: Natural bell curve
Daily: Weekdays > Weekends
```

### Real-time Metrics:
```
Events (5m): 50-200 (if actively simulating)
Top Event: pageview (60-70%)
Top Page: /home (30-40%)
```

---

## 🎉 Done!

Bây giờ bạn có:
- ✅ Dữ liệu realistic với 5 user personas
- ✅ Time Analysis đầy đủ (Peak + Hourly + Daily)
- ✅ Real-time Metrics (5 min, auto-update)
- ✅ Spark analysis cho insights có ý nghĩa

Enjoy! 🚀
