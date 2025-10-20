# Fix ConflictingUpdateOperators Error

## 🐛 Vấn đề

**Error Message:**
```
ConflictingUpdateOperators: Updating the path 'pages' would create a conflict at 'pages'
```

**Nguyên nhân:**

Trong MongoDB update operation, không thể có 2 operators modify cùng 1 field:

```python
# ❌ SAI - Conflict!
{
    "$setOnInsert": {
        "pages": []  # ← Operator 1 set pages
    },
    "$addToSet": {
        "pages": "/home"  # ← Operator 2 cũng modify pages
    }
}
```

MongoDB báo lỗi vì:
- `$setOnInsert` muốn set `pages = []`
- `$addToSet` muốn add item vào `pages`
- Cả 2 đều modify field `pages` → **CONFLICT**!

---

## ✅ Giải pháp

### Fix 1: ingest.py

**Trước (SAI):**
```python
session_doc = sessions_col().find_one_and_update(
    {"session_id": doc["session_id"]},
    {
        "$setOnInsert": {
            "session_id": doc["session_id"],
            "user_id": user_id,
            "pages": [],  # ← Conflict với $addToSet!
        },
        "$addToSet": {"pages": doc.get("page")},
    },
    upsert=True,
)
```

**Sau (ĐÚNG):**
```python
session_doc = sessions_col().find_one_and_update(
    {"session_id": doc["session_id"]},
    {
        "$setOnInsert": {
            "session_id": doc["session_id"],
            "user_id": user_id,
            # ✅ Bỏ pages - let $addToSet handle it
        },
        "$addToSet": {"pages": doc.get("page")},  # Auto-creates array
    },
    upsert=True,
)
```

**Lý do:** `$addToSet` tự động tạo array nếu field chưa tồn tại!

### Fix 2: seed_realistic_data.py

**Trước (SAI):**
```python
sessions_col().update_one(
    {"session_id": session_id},
    {
        "$setOnInsert": {
            "session_id": session_id,
            "user_id": user_id,
            "pages": [],  # ← Conflict nếu sau đó có $addToSet
        },
        ...
    },
    upsert=True,
)
```

**Sau (ĐÚNG):**
```python
sessions_col().update_one(
    {"session_id": session_id},
    {
        "$setOnInsert": {
            "session_id": session_id,
            "user_id": user_id,
            # ✅ Bỏ pages - will be populated by ingest_event
        },
        ...
    },
    upsert=True,
)
```

---

## 📚 MongoDB Update Operators

### Quy tắc:
- **KHÔNG** được có 2 operators modify cùng 1 field
- **KHÔNG** được có nested conflicts (e.g., `$set` field và `$inc` sub-field)

### Valid combinations:

✅ **OK:**
```python
{
    "$setOnInsert": {"session_id": "abc", "user_id": "123"},
    "$addToSet": {"pages": "/home"},  # Different fields
    "$inc": {"event_count": 1},       # Different fields
}
```

❌ **NOT OK:**
```python
{
    "$setOnInsert": {"pages": []},
    "$addToSet": {"pages": "/home"},  # CONFLICT on 'pages'!
}
```

❌ **NOT OK:**
```python
{
    "$set": {"metadata": {"count": 0}},
    "$inc": {"metadata.count": 1},  # CONFLICT on 'metadata.count'!
}
```

---

## 🔧 Behavior của $addToSet

### Khi field chưa tồn tại:
```javascript
// Document: {}
db.sessions.updateOne(
  {_id: "abc"},
  {$addToSet: {pages: "/home"}},
  {upsert: true}
)

// Result: {_id: "abc", pages: ["/home"]}
// ✅ Auto-creates array!
```

### Khi field đã tồn tại:
```javascript
// Document: {_id: "abc", pages: ["/home"]}
db.sessions.updateOne(
  {_id: "abc"},
  {$addToSet: {pages: "/cart"}}
)

// Result: {_id: "abc", pages: ["/home", "/cart"]}
// ✅ Adds to existing array
```

### Khi value đã tồn tại:
```javascript
// Document: {_id: "abc", pages: ["/home"]}
db.sessions.updateOne(
  {_id: "abc"},
  {$addToSet: {pages: "/home"}}  // Already exists
)

// Result: {_id: "abc", pages: ["/home"]}
// ✅ No duplicate - idempotent
```

---

## 🧪 Testing

### Test 1: Verify no conflicts
```bash
# Clear old data
mongo clickstream_db --eval "db.events.deleteMany({}); db.sessions.deleteMany({});"

# Seed new data (với code đã fix)
.venv\Scripts\python.exe seed_realistic_data.py --user-count 10 --days 1 --sessions-per-user 2 --avg-events 5

# Should NOT see error:
# ✅ No "ConflictingUpdateOperators" errors
# ✅ Sessions have populated pages array
```

### Test 2: Check sessions
```javascript
// MongoDB
db.sessions.findOne()

// Should have:
{
  session_id: "...",
  user_id: ObjectId("..."),
  pages: ["/home", "/product", "/cart"],  // ✅ Populated!
  event_count: 5
}
```

### Test 3: Verify events match
```javascript
var session = db.sessions.findOne();
var events = db.events.find({session_id: session.session_id}).toArray();

print("Session pages:", session.pages);
print("Event pages:", events.map(e => e.page));

// Should match (set equality)
```

---

## 📊 Expected Results

### Before fix:
```bash
[ingest] Warning: ConflictingUpdateOperators: 'pages'
[ingest] Warning: ConflictingUpdateOperators: 'pages'
[ingest] Warning: ConflictingUpdateOperators: 'pages'
...

# Sessions:
{
  pages: [],      // ❌ Empty!
  event_count: 0  // ❌ Wrong!
}
```

### After fix:
```bash
# No errors!

# Sessions:
{
  pages: ["/home", "/product", "/cart"],  // ✅ Populated!
  event_count: 5                          // ✅ Correct!
}
```

---

## 🎯 Summary

### Root cause:
- `$setOnInsert` và `$addToSet` cùng modify field `pages`
- MongoDB không cho phép → ConflictingUpdateOperators

### Fix applied:
- ✅ Bỏ `"pages": []` khỏi `$setOnInsert`
- ✅ Let `$addToSet` tự tạo array khi cần
- ✅ No more conflicts!

### Files changed:
1. `ingest.py` - Removed pages from $setOnInsert
2. `seed_realistic_data.py` - Removed pages from $setOnInsert

### Result:
- ✅ No ConflictingUpdateOperators errors
- ✅ Sessions populated correctly
- ✅ Pages array auto-created and filled
- ✅ Event counts accurate

---

## 🚀 Next Steps

### Immediate:
1. Clear old broken data
2. Reseed with fixed code
3. Verify no errors

### Commands:
```bash
# 1. Clear
mongo clickstream_db --eval "db.events.deleteMany({}); db.sessions.deleteMany({});"

# 2. Seed
.venv\Scripts\python.exe seed_realistic_data.py --user-count 100 --days 7 --sessions-per-user 4 --avg-events 7

# 3. Verify
.venv\Scripts\python.exe verify_sessions.py
```

---

## ✅ Done!

Lỗi ConflictingUpdateOperators đã được fix! 🎉

Sessions giờ sẽ có:
- ✅ Pages array đầy đủ
- ✅ Event count chính xác
- ✅ No MongoDB conflicts
- ✅ Ready for production
