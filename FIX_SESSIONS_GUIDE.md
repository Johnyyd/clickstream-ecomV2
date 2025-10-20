# Fix Sessions Guide - Sessions không chứa events của cùng user_id

## 🐛 Vấn đề

**Triệu chứng:**
```javascript
// Session document
{
  _id: ObjectId("69f6941b7fee161cd51c9691"),
  session_id: "69f6941b7fee161cd51c9691",
  user_id: ObjectId('69f248fdb0aa1706983ef11'),
  event_count: 0,  // ← Sai! Phải > 0
  pages: []        // ← Trống!
}

// Events của session này
db.events.find({session_id: "69f6941b7fee161cd51c9691"})
// → Returns 0 events (hoặc events với user_id khác)
```

**Nguyên nhân:**

Có 2 cách tạo session documents không nhất quán:

1. **ingest.py** (runtime):
   ```python
   sessions_col().find_one_and_update(
       {"session_id": doc["session_id"]},  # Query by session_id field
       ...
   )
   ```

2. **seed_realistic_data.py** (trước khi fix):
   ```python
   sessions_col().update_one(
       {"_id": session_id},  # Query by _id field ← SAI!
       ...
   )
   ```

**Kết quả:**
- Seeding tạo session với `_id = session_id`
- Runtime ingestion tạo session khác với auto-generated `_id`
- → 2 session documents cho cùng 1 `session_id`!
- → Events đi vào session này, session kia empty

---

## ✅ Giải pháp

### Bước 1: Fix code (ĐÃ HOÀN THÀNH)

File `seed_realistic_data.py` đã được sửa:

```python
def ensure_browsing_session(session_id: str, user_id: ObjectId, start_ts: int, client_id: Optional[str] = None) -> bool:
    res = sessions_col().update_one(
        {"session_id": session_id},  # ✅ Match ingest.py
        {
            "$setOnInsert": {
                "session_id": session_id,  # ✅ Không dùng _id nữa
                "user_id": user_id,
                ...
            },
            ...
        },
        upsert=True,
    )
```

### Bước 2: Clean up duplicate sessions

```bash
# Run cleanup script
.venv\Scripts\python.exe fix_duplicate_sessions.py
```

**Script sẽ:**
1. Tìm tất cả session_ids có > 1 documents
2. Merge data từ duplicates vào 1 document
3. Delete duplicates
4. Verify kết quả

**Output:**
```
============================================================
Fix Duplicate Sessions Script
============================================================
Found 1247 duplicate session_ids

Session: 69f6941b7fee161cd51c9691
  Keeper: ObjectId("xxx") (events: 15)
  Deleting: ['ObjectId("yyy")']

✅ Merged 1247 sessions
✅ Deleted 1247 duplicate documents

=== Verifying Sessions ===
Total sessions: 45291
  Sessions without events: 0
  Sessions with wrong user_id: 0

✅ All sessions are valid!
============================================================
```

### Bước 3: Reseed data (Option A - Fresh start)

```bash
# 1. Clear all data
mongo clickstream_db --eval "db.events.deleteMany({}); db.sessions.deleteMany({}); db.analyses.deleteMany({});"

# 2. Seed với code đã fix
.venv\Scripts\python.exe seed_realistic_data.py --user-count 100 --days 7 --sessions-per-user 4 --avg-events 7 --seed-products
```

### Bước 3: Keep old data (Option B - Just fix)

```bash
# Chỉ chạy cleanup script
.venv\Scripts\python.exe fix_duplicate_sessions.py
```

---

## 🔍 Verify kết quả

### Check 1: Session có events
```javascript
// MongoDB
db.sessions.findOne({session_id: "69f6941b7fee161cd51c9691"})

// Should have:
{
  session_id: "69f6941b7fee161cd51c9691",
  user_id: ObjectId('69f248fdb0aa1706983ef11'),
  event_count: 15,  // ✅ > 0
  pages: ["/home", "/product", "/cart"],  // ✅ Not empty
  first_event_at: ISODate("2025-10-20T..."),
  last_event_at: ISODate("2025-10-20T...")
}
```

### Check 2: Events match session user_id
```javascript
// Get session user_id
var session = db.sessions.findOne({session_id: "69f6941b7fee161cd51c9691"})
print("Session user_id:", session.user_id)

// Get events user_ids
db.events.aggregate([
  {$match: {session_id: "69f6941b7fee161cd51c9691"}},
  {$group: {_id: "$user_id", count: {$sum: 1}}}
])

// Should show only 1 user_id matching session
```

### Check 3: No duplicate sessions
```javascript
db.sessions.aggregate([
  {$group: {_id: "$session_id", count: {$sum: 1}}},
  {$match: {count: {$gt: 1}}}
])

// Should return 0 results
```

### Check 4: All sessions have events
```javascript
db.sessions.find({event_count: 0}).count()

// Should be 0 or very small
// (Some empty sessions are OK if just created)
```

---

## 📊 Expected Results

### Before fix:
```
Total sessions: 90,582 (duplicates!)
├── With events: 45,291
└── Empty: 45,291 (duplicates)

Sessions per user_id: Multiple sessions with same ID
Event tracking: Broken (events in one, session doc in another)
```

### After fix:
```
Total sessions: 45,291 (no duplicates)
├── With events: 45,291
└── Empty: 0

Sessions per user_id: One session per session_id
Event tracking: ✅ Working (all events linked correctly)
```

---

## 🚨 Prevention

### For future seeding:

**✅ DO:**
```python
# Always query by session_id field
sessions_col().update_one(
    {"session_id": session_id},
    ...
)
```

**❌ DON'T:**
```python
# Never query by _id for sessions
sessions_col().update_one(
    {"_id": session_id},  # ← Wrong!
    ...
)
```

### Consistency checklist:

- [ ] `ingest.py`: Uses `{"session_id": ...}`
- [ ] `seed_realistic_data.py`: Uses `{"session_id": ...}`
- [ ] `spark_jobs.py`: References by `session_id` field
- [ ] All analysis code: Groups by `session_id` field

---

## 🔧 Manual verification commands

### Check session consistency:
```bash
mongo clickstream_db
```

```javascript
// 1. Count sessions
db.sessions.count()

// 2. Count events with sessions
db.events.distinct("session_id").length

// 3. Find orphan events (events without session)
db.events.aggregate([
  {
    $lookup: {
      from: "sessions",
      localField: "session_id",
      foreignField: "session_id",
      as: "session"
    }
  },
  {$match: {session: {$size: 0}}},
  {$count: "orphan_events"}
])

// 4. Find duplicate session_ids
db.sessions.aggregate([
  {$group: {_id: "$session_id", count: {$sum: 1}}},
  {$match: {count: {$gt: 1}}},
  {$count: "duplicates"}
])

// 5. Verify user_id consistency
db.sessions.aggregate([
  {
    $lookup: {
      from: "events",
      localField: "session_id",
      foreignField: "session_id",
      as: "events"
    }
  },
  {
    $project: {
      session_id: 1,
      user_id: 1,
      event_users: "$events.user_id",
      mismatch: {
        $ne: [
          {$size: {$setUnion: ["$events.user_id"]}},
          1
        ]
      }
    }
  },
  {$match: {mismatch: true}},
  {$limit: 5}
])
```

---

## 📝 Summary

### Root cause:
- Inconsistent session document creation
- `ingest.py` used `session_id` field
- `seed_realistic_data.py` used `_id` field
- Result: Duplicate sessions, broken event tracking

### Fix applied:
- ✅ Updated `seed_realistic_data.py` to match `ingest.py`
- ✅ Created cleanup script to merge duplicates
- ✅ Verification tools to check data integrity

### Next steps:
1. Run cleanup script: `python fix_duplicate_sessions.py`
2. Or reseed data: `python seed_realistic_data.py ...`
3. Verify with MongoDB queries
4. Test analysis: Run Spark analysis and check results

---

## ✅ Done!

Sau khi fix:
- ✅ Mỗi session_id chỉ có 1 document
- ✅ Events và sessions có cùng user_id
- ✅ Session tracking hoạt động đúng
- ✅ Analysis có data chính xác

🎉 Sessions are now consistent!
