# Quick Fix - Sessions Empty Pages

## 🐛 Vấn đề
Sessions có `pages: []` và `event_count: 0` mặc dù có timestamps và events tồn tại.

## ⚡ Fix Ngay (3 bước)

### 1. Verify vấn đề
```bash
.venv\Scripts\python.exe verify_sessions.py
```

### 2. Fix sessions
```bash
.venv\Scripts\python.exe fix_empty_sessions.py
```

### 3. Verify lại
```bash
.venv\Scripts\python.exe verify_sessions.py
```

## ✅ Kết quả

**Trước:**
```javascript
{
  session_id: "69f6944cd5b294f2e06ba04",
  event_count: 0,        // ❌
  pages: []              // ❌
}
```

**Sau:**
```javascript
{
  session_id: "69f6944cd5b294f2e06ba04",
  event_count: 15,       // ✅
  pages: ["/home", "/product", "/cart"]  // ✅
}
```

## 📝 Chi tiết

Xem: `FIX_EMPTY_PAGES_GUIDE.md`

---

## 🚨 Nếu vẫn gặp vấn đề

### Option 1: Reseed data
```bash
# Clear
mongo clickstream_db --eval "db.events.deleteMany({}); db.sessions.deleteMany({});"

# Seed new
.venv\Scripts\python.exe seed_realistic_data.py --user-count 100 --days 7 --sessions-per-user 4 --avg-events 7
```

### Option 2: Manual fix trong MongoDB
```javascript
db.sessions.find({event_count: 0}).forEach(function(session) {
  var events = db.events.find({session_id: session.session_id}).toArray();
  if (events.length === 0) return;
  
  db.sessions.updateOne(
    {_id: session._id},
    {$set: {
      pages: [...new Set(events.map(e => e.page))],
      event_count: events.length
    }}
  );
});
```

---

## 🎯 Done!

✅ Sessions fixed
✅ Pages populated  
✅ Event counts accurate
✅ Ready for analysis

🚀 Run analysis now!
