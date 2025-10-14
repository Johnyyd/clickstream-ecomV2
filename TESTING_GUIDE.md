# 🧪 Testing Guide - Dashboard Improvements

## 🚀 Quick Start

### 1. Set Provisioning Key (Bắt buộc cho auto-renewal)
```powershell
$env:OPENROUTER_PROVISIONING_KEY="sk-or-v1-your-provisioning-key-here"
```

### 2. Start Server
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Open Dashboard
```
http://localhost:8000/dashboard
```

---

## ✅ Test Checklist

### Test 1: Login & Auto API Key
- [ ] Login với username/password
- [ ] Kiểm tra console log: "✅ Provisioning key available - auto-renewal enabled"
- [ ] Không cần paste API key thủ công

### Test 2: Generate Data
- [ ] Click "Simulate Events (10)"
- [ ] Thấy message: "10 events ingested successfully"

### Test 3: Run Analysis
- [ ] Click "Run Analysis"
- [ ] Đợi khoảng 10-15 giây
- [ ] Kiểm tra console logs:
  ```
  [Auto-Renewal] Calling OpenRouter API...
  ✅ API key was automatically renewed (nếu là lần đầu)
  ```

### Test 4: Kiểm tra LLM Display

#### 4.1 Executive Summary
- [ ] Có section "📊 Executive Summary"
- [ ] Background gradient purple đẹp
- [ ] Text 2-3 câu tóm tắt

#### 4.2 KPIs Grid
- [ ] Có 4 KPI cards:
  - Total Events
  - Total Sessions
  - Bounce Rate
  - Avg Session Duration
- [ ] Hover vào card → card nâng lên (transform)
- [ ] Background gradient đẹp

#### 4.3 Key Insights
- [ ] Có numbered list (1, 2, 3...)
- [ ] Mỗi insight có background xám nhạt
- [ ] Border trái màu xanh

#### 4.4 Traffic Insights
- [ ] Có 3 subsections:
  - Peak Hours
  - User Behavior Patterns
  - Popular Categories
- [ ] Mỗi subsection có background riêng

#### 4.5 Conversion Analysis
- [ ] Có 3 subsections:
  - Funnel Performance (màu xanh lá)
  - Drop-off Points (màu vàng)
  - Optimization Opportunities (màu xanh dương)
- [ ] Color coding rõ ràng

#### 4.6 Business Recommendations
- [ ] List với checkmark icons
- [ ] Background màu xanh lá nhạt
- [ ] Border trái màu xanh lá

#### 4.7 Strategic Decisions
- [ ] Numbered list với background vàng
- [ ] Font weight bold
- [ ] Border trái màu cam

#### 4.8 Next Best Actions
- [ ] Interactive checklist
- [ ] Click checkbox → text có line-through
- [ ] Hover → background đổi màu

#### 4.9 Risk Alerts
- [ ] Warning icons ⚠️
- [ ] Background màu đỏ nhạt
- [ ] Text màu đỏ đậm

#### 4.10 User Recommendations
- [ ] List với background xanh dương nhạt
- [ ] Border trái màu xanh dương

#### 4.11 Product Recommendations
- [ ] Product cards grid
- [ ] Hover → border xanh, shadow, nâng lên
- [ ] Link "View Product →" hoạt động

#### 4.12 Raw Data
- [ ] Collapsible `<details>` element
- [ ] Click summary → expand JSON
- [ ] JSON có syntax highlighting (màu xanh lá)

---

## 🐛 Troubleshooting

### Lỗi: "OPENROUTER_PROVISIONING_KEY not set"
**Giải pháp:**
```powershell
$env:OPENROUTER_PROVISIONING_KEY="sk-or-v1-your-key"
```

### Lỗi: "401 Unauthorized"
**Nguyên nhân:** Provisioning key không hợp lệ
**Giải pháp:**
1. Kiểm tra lại key từ https://openrouter.ai/
2. Đảm bảo key có quyền tạo runtime keys

### Lỗi: LLM response bị cắt ngắn
**Nguyên nhân:** max_tokens quá thấp
**Giải pháp:** Đã fix - max_tokens = 2000

### Lỗi: Không hiển thị traffic_insights hoặc conversion_analysis
**Nguyên nhân:** LLM không trả về đủ data
**Giải pháp:**
1. Kiểm tra prompt trong `openrouter_client.py`
2. Tăng max_tokens nếu cần
3. Check raw JSON để xem LLM trả về gì

### Lỗi: CSS không load
**Giải pháp:**
1. Hard refresh: Ctrl + Shift + R
2. Check console: có lỗi 404 không?
3. Verify file exists: `static/llmDisplay.css`

---

## 📊 Expected Output

### Console Logs (Success):
```
Server running on http://localhost:8000/dashboard
✅ Provisioning key available - auto-renewal enabled
Preparing OpenRouter API call with auto-renewal support...
[Auto-Renewal] Calling OpenRouter API...
[OpenRouter] Endpoint=https://openrouter.ai/api/v1/chat/completions Model=z-ai/glm-4.5-air:free MaxTokens=2000 Temp=0.3
✅ API key was automatically renewed during this request (nếu lần đầu)
LLM analysis completed successfully
Saved comprehensive analysis record with ID: ...
```

### Browser Console (Success):
```
Logged in!
Running analysis with Spark...
Analysis completed
Displaying LLM analysis...
```

### Visual Check:
- ✅ 11 sections hiển thị đầy đủ
- ✅ Colors đúng theme
- ✅ Hover effects hoạt động
- ✅ Responsive trên mobile
- ✅ Không có lỗi layout

---

## 🎯 Performance Metrics

### Expected Timing:
- Login: < 1s
- Simulate Events: < 2s
- Run Analysis: 10-15s (bao gồm LLM call)
- Display Results: < 1s

### LLM Response:
- Status: "ok"
- Parsed: object với 11+ keys
- Auto-renewed: true (nếu lần đầu)
- Error: null

---

## 📸 Screenshots to Take

1. Executive Summary section
2. KPIs Grid (4 cards)
3. Key Insights list
4. Traffic Insights (3 subsections)
5. Conversion Analysis (3 subsections)
6. Product Recommendations grid
7. Interactive checklist (với checkbox checked)
8. Raw JSON (expanded)

---

## ✨ Bonus Tests

### Test Auto-Renewal:
1. Xóa API key khỏi database:
   ```python
   from db import api_keys_col
   api_keys_col().delete_many({"provider": "openrouter"})
   ```
2. Run analysis
3. Check logs: "✅ API key was automatically renewed"
4. Verify key saved in DB

### Test Manual Key (Optional):
1. Expand "Advanced: Manual Key Management"
2. Paste key
3. Click "Save Key"
4. Click "Check Key"
5. Verify masked key displayed

### Test Responsive:
1. Resize browser → mobile width
2. Check grid layouts collapse to 1 column
3. Check cards stack vertically
4. All content readable

---

## 🎉 Success Criteria

✅ All 11 LLM sections display correctly
✅ Colors and styling match design
✅ Interactive elements work (checkboxes, hover)
✅ API key auto-managed (no manual input needed)
✅ No console errors
✅ Responsive design works
✅ Performance < 15s total

---

**Happy Testing! 🚀**
