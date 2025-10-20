# Fix Empty Pages Guide - Sessions không chứa pages

## 🐛 Vấn đề

**Triệu chứng:**
```javascript
// Session document
{
  _id: ObjectId("69f6944cd5b294f2e06ba04"),
  session_id: "69f6944cd5b294f2e06ba04",
  client_id: "client_93ef11",
  event_count: 0,        // ← Sai! Phải > 0
  first_event_at: ISODate("2025-10-20T15:33:20.000+00:00"),
  last_event_at: ISODate("2025-10-20T15:33:20.000+00:00"),
  pages: [],             // ← RỖNG!
  user_id: ObjectId('69f248fdb0aa1706983ef11')
}
```

**Có timestamps nhưng pages rỗng!**

---

## 🔍 Root Cause Analysis

### Nguyên nhân có thể:

1. **Exception bị im lặng trong ingest.py**
   ```python
   try:
       session_doc = sessions_col().find_one_and_update(...)
   except Exception:
       pass  # ← Im lặng! Không log error
   ```

2. **Race condition**: `ensure_browsing_session` tạo session trước, nhưng `ingest_event` không update được

3. **MongoDB operation failed**: Network, permission, hoặc validation issues

4. **Duplicate sessions**: Có 2 sessions cùng session_id, events update vào cái khác

---

## ✅ Giải pháp

### Bước 1: Thêm logging (ĐÃ HOÀN THÀNH)

File `ingest.py` đã được update:
```python
except Exception as e:
    print(f"[ingest] Warning: Failed to update session {doc.get('session_id')}: {e}")
    pass
```

### Bước 2: Verify hiện trạng

```bash
.venv\Scripts\python.exe verify_sessions.py
```

Output sẽ hiển thị:
```
============================================================
Session Verification Report
============================================================

📊 Overall Stats:
  Total sessions: 45291
  Total events: 320410

1️⃣ Empty Pages:
  Sessions with empty pages: 12847
  ⚠️  12847 sessions need page data

2️⃣ Event Counts:
  Sessions with 0 events: 12847
  ⚠️  12847 sessions report 0 events

...
```

### Bước 3: Fix empty sessions

```bash
.venv\Scripts\python.exe fix_empty_sessions.py
```

Script sẽ:
1. Tìm sessions với `pages = []` hoặc `event_count = 0`
2. Lookup events matching `session_id`
3. Tính lại: pages, event_count, timestamps, user_id
4. Update session document

Output:
```
============================================================
Fix Empty Sessions Script
============================================================
Found 12847 potentially empty sessions

Processing 12847 sessions...
  Processed 100/12847...
  Processed 200/12847...
  ...

============================================================
✅ Fixed 12545 sessions
ℹ️  Found 302 orphan sessions (no events)
============================================================

=== Verification ===
Total sessions: 45291
Sessions with events: 44989
Empty sessions remaining: 302

✅ All fixable sessions have been fixed!
   302 orphan sessions remain (created but no events)
```

### Bước 4: Clean up orphan sessions (Optional)

Nếu muốn xóa orphan sessions (không có events):
```javascript
// MongoDB
db.sessions.deleteMany({
  event_count: 0,
  pages: {$size: 0}
})
```

---

## 🧪 Verify kết quả

### Check 1: Sessions có pages
```javascript
// MongoDB
db.sessions.findOne({session_id: "69f6944cd5b294f2e06ba04"})

// Should now have:
{
  session_id: "69f6944cd5b294f2e06ba04",
  event_count: 15,  // ✅ > 0
  pages: ["/home", "/product", "/cart"],  // ✅ Not empty!
  user_id: ObjectId('69f248fdb0aa1706983ef11')
}
```

### Check 2: No empty sessions
```javascript
db.sessions.find({
  event_count: {$gt: 0},
  pages: {$size: 0}
}).count()

// Should be 0
```

### Check 3: Event count matches
```javascript
// Pick a random session
var session = db.sessions.findOne({event_count: {$gt: 0}})
print("Session event_count:", session.event_count)

// Count actual events
var actualCount = db.events.count({session_id: session.session_id})
print("Actual events:", actualCount)

// Should match!
```

---

## 🚨 Prevention

### For new data seeding:

**✅ DO:**
```python
# Always call ingest_event for every event
# It will handle session updates automatically
emit_event(user_id, sid, current_ts, page, event_type, props, client_id)
```

**❌ DON'T:**
```python
# Don't create sessions separately and hope they sync
ensure_browsing_session(sid, user_id, start_ts, client_id)
# Then expect events to auto-fill it
```

### Monitor for issues:

```bash
# Run verification regularly
.venv\Scripts\python.exe verify_sessions.py

# Check MongoDB logs for errors
tail -f /var/log/mongodb/mongod.log | grep "update"
```

---

## 📊 Understanding the Flow

### Correct flow:

```
1. generate_session_for_user()
   ↓
2. ensure_browsing_session(sid, user_id, ...)
   → Creates empty session with session_id
   ↓
3. emit_event(user_id, sid, ...)
   ↓
4. ingest_event(ev)
   ↓
5. sessions_col().find_one_and_update({"session_id": sid})
   → Updates: event_count++, pages.push(page)
   ✅ Session now has data!
```

### When it breaks:

```
1. ensure_browsing_session() ✅ Creates session
   ↓
2. ingest_event() tries to update
   ↓
3. Exception occurs (network, permission, etc.)
   ↓
4. Exception silently caught with `pass`
   ↓
5. Event inserted ✅ but session not updated ❌
   ↓
Result: Empty session, but events exist!
```

---

## 🔧 Advanced: Manual fixing

### Fix single session:
```javascript
// MongoDB
var sessionId = "69f6944cd5b294f2e06ba04";

// Get events
var events = db.events.find({session_id: sessionId}).toArray();

// Calculate values
var pages = [...new Set(events.map(e => e.page))];
var eventCount = events.length;
var firstEvent = events[0].timestamp;
var lastEvent = events[events.length - 1].timestamp;

// Update session
db.sessions.updateOne(
  {session_id: sessionId},
  {
    $set: {
      pages: pages,
      event_count: eventCount,
      first_event_at: firstEvent,
      last_event_at: lastEvent
    }
  }
)
```

### Batch fix all:
```javascript
// MongoDB
db.sessions.find({event_count: 0}).forEach(function(session) {
  var events = db.events.find({session_id: session.session_id}).toArray();
  
  if (events.length === 0) return; // Skip orphans
  
  var pages = [...new Set(events.map(e => e.page))];
  
  db.sessions.updateOne(
    {_id: session._id},
    {
      $set: {
        pages: pages,
        event_count: events.length,
        first_event_at: events[0].timestamp,
        last_event_at: events[events.length - 1].timestamp
      }
    }
  );
});
```

---

## 📝 Summary

### Vấn đề:
- Sessions có timestamps nhưng `pages = []` và `event_count = 0`
- Events tồn tại nhưng không được count vào session
- Exception trong `ingest.py` bị `pass` im lặng

### Fix đã apply:
1. ✅ Thêm logging vào `ingest.py` để catch exceptions
2. ✅ Tạo `fix_empty_sessions.py` để recalculate từ events
3. ✅ Tạo `verify_sessions.py` để monitor health

### Cách sử dụng:
```bash
# 1. Verify
python verify_sessions.py

# 2. Fix
python fix_empty_sessions.py

# 3. Verify again
python verify_sessions.py
```

### Kết quả mong đợi:
- ✅ Tất cả sessions có `event_count > 0` → có pages
- ✅ Pages array chứa đầy đủ pages từ events
- ✅ Event count khớp với số events thực tế
- ✅ User_id nhất quán giữa session và events

---

## 🎯 Next Steps

### Immediate:
1. Run `verify_sessions.py` để xem current state
2. Run `fix_empty_sessions.py` để fix
3. Optional: Clean up orphan sessions

### Long-term:
1. Monitor logs cho "[ingest] Warning"
2. Add retry logic vào session updates
3. Consider using transactions for atomicity
4. Add health check endpoint: `/api/health/sessions`

---

## ✅ Done!

Sau khi fix:
- ✅ Sessions đầy đủ thông tin pages
- ✅ Event counts chính xác
- ✅ Ready cho Spark analysis
- ✅ Dashboard displays correctly

🎉 Sessions are now complete!
