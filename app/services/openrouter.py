"""
OpenRouter AI service
"""
import httpx
from typing import Dict, Optional
from app.core.config import settings
import logging

async def analyze_user_behavior(user_id: str, api_key: str, db) -> Dict:
    """
    Analyze user behavior patterns using OpenRouter AI
    """
    user_data = await db.events.get_user_events(user_id)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OPENROUTER_API_URL}",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"user_data": user_data}
        )
        response.raise_for_status()
        return response.json()

async def analyze_ml_results(ml_results: Dict, api_key: Optional[str] = None) -> Dict:
    """
    Summarize existing ML analytics outputs (segmentation, retention, recommendations, etc.)
    using the OpenRouter backend if configured. If not configured, return a basic fallback
    summary so the UI still shows something.

    Args:
        ml_results: Dict of module results as computed by Spark jobs
        api_key: Optional override. If None, will try to use settings.OPENROUTER_API_KEY

    Returns:
        Dict containing a 'insights' narrative and optional 'highlights' bullets
    """
    try:
        base_url = getattr(settings, "OPENROUTER_API_URL", None) or "https://openrouter.ai/api/v1"

        raw_key = api_key
        if not raw_key:
            s_key = getattr(settings, "OPENROUTER_API_KEY", None)
            if s_key is not None and not isinstance(s_key, str):
                try:
                    s_key = s_key.get_secret_value()
                except Exception:
                    pass
            raw_key = s_key

        key = raw_key

        logger = logging.getLogger(__name__)
        logger.info("analyze_ml_results: base_url=%s, key_present=%s, api_key_arg=%s", base_url, bool(key), bool(api_key))

        if base_url and key:
            # System-style prompt: phân tích chuyên sâu dữ liệu analytics cho quản trị viên e‑commerce (tiếng Việt)
            prompt = (
                "Bạn là chuyên gia analytics & growth cho sản phẩm e‑commerce. \n"
                "Nhiệm vụ: đọc JSON analytics (ml_results) là TỔNG HỢP KẾT QUẢ từ nhiều API/backend module khác nhau và tạo một BÁO CÁO CHUYÊN SÂU giúp quản trị viên hiểu nhanh tình hình dữ liệu và ra quyết định.\n\n"
                "DỮ LIỆU ĐẦU VÀO (ml_results):\n"
                "- Là một object gồm nhiều module con, ví dụ: business, overview, journey, cart, seo, activity, retention, experiments, recommendations, ml_prediction (tổng hợp từ nhiều phân tích), v.v.\n"
                "- Mỗi module tương ứng với một API hoặc job phân tích trong backend, có thể chứa KPI, timeseries, phân phối, danh sách top‑N, v.v.\n"
                "- Cụ thể thường có:\n"
                "  • business: total_sessions, total_users, orders, revenue, aov, conversion_rate, data_quality…\n"
                "  • journey: funnel.steps (name/step, value/count), top_paths hoặc links, các bước có drop‑off cao.\n"
                "  • seo: site_metrics (total_views, unique_visitors, bounce_rate…), sources.distribution, traffic_trend theo thời gian.\n"
                "  • activity: activity_hourly[24], dow[7], by_date[{date,count}], peak_day, peak_hour, top_hours[{hour,label,count,pct}], top_days[{date,count}].\n"
                "  • retention: timeseries[{date, retained, churned}] hoặc các trường tương đương.\n"
                "  • ml_prediction (hoặc các module tổng hợp khác): có thể chứa kết quả tổng hợp từ nhiều API/backend, hãy dùng để kiểm tra chéo với các module gốc.\n"
                "  • các module khác (nếu có) thì hãy tự đọc key và nội dung để suy luận chức năng (ví dụ: cart, recommendations, experiments, raw_metrics…).\n"
                "Một số field có thể thiếu hoặc = null – luôn kiểm tra tồn tại trước khi dùng, tuyệt đối KHÔNG bịa số.\n\n"
                "YÊU CẦU ĐẦU RA: TRẢ VỀ DUY NHẤT 1 JSON với SCHEMA CHÍNH XÁC sau (key tiếng Anh, nội dung có thể tiếng Việt):\n"
                "{\n"
                "  'executive_summary': string,\n"
                "  'insights': {\n"
                "    'business': string[],\n"
                "    'journey': string[],\n"
                "    'seo': string[],\n"
                "    'retention': string[]\n"
                "  },\n"
                "  'recommendations': string[],\n"
                "  'kpis': {\n"
                "    'sessions': number,\n"
                "    'users': number,\n"
                "    'cr': number,\n"
                "    'revenue': number,\n"
                "    'aov': number|null\n"
                "  },\n"
                "  'charts': {\n"
                "    'funnel': { 'name': string, 'value': number }[],\n"
                "    'seo_distribution': { 'name': string, 'value': number }[],\n"
                "    'retention_timeseries': { 'date': string, 'retained': number, 'churned': number }[],\n"
                "    'data_quality': {\n"
                "      'events_count': number|null,\n"
                "      'sessions_count': number|null,\n"
                "      'missing_values_pct': number|null,\n"
                "      'duplicate_events_pct': number|null,\n"
                "      'last_event_ts': string|null\n"
                "    }\n"
                "  }\n"
                "}.\n\n"
                "HƯỚNG DẪN PHÂN TÍCH CHUYÊN SÂU (HÃY ÁP DỤNG CÁC KỸ THUẬT PHÂN TÍCH NGHIỆP VỤ & THỐNG KÊ ĐƠN GIẢN VÀ NHẬN XÉT KỸ VỀ CHÍNH DỮ LIỆU ĐẦU VÀO):\n"
                "- Bước 1: ĐỌC TỪNG MODULE (MỖI KEY TOP-LEVEL = 1 API/MODULE): với MỌI key chính trong ml_results (business, journey, cart, seo, activity, retention, ml_prediction, v.v.), hãy tóm tắt module đó đo lường điều gì và các số quan trọng nhất. KHÔNG được bỏ sót module nào khi có dữ liệu. ĐẶC BIỆT: nếu tồn tại 'cart' hoặc 'ml_prediction' với dữ liệu không rỗng thì BẮT BUỘC phải được đề cập MINIMUM 1–2 lần trong 'insights' hoặc 'executive_summary'.\n"
                "- Bước 2: PHÂN TÍCH BÊN TRONG MỖI MODULE: tính toán/ước lượng các tỷ lệ, so sánh nội bộ (vd: bước funnel nào rớt nhiều nhất, kênh nào chiếm nhiều traffic nhất, cart abandonment bao nhiêu %). ĐẶC BIỆT VỚI MODULE 'cart': nếu tồn tại 'cart.metrics' hoặc 'cart.channels' hoặc 'size_distribution' thì PHẢI trích xuất và nêu rõ ÍT NHẤT 1–2 con số cụ thể (tỷ lệ %, số lượng giỏ, abandonment_rate theo kênh, v.v.) trong phần insights hoặc executive_summary, ví dụ đọc từ 'cart.metrics.abandonment_rate', 'cart.channels[referral].abandonment_rate', 'size_distribution'.\n"
                "- Bước 3: KẾT NỐI GIỮA CÁC MODULE: liên kết tín hiệu giữa business, journey, cart, seo, retention, activity, ml_prediction để tìm ra nguyên nhân gốc (vd: CR thấp đến từ kênh nào hoặc bước funnel nào, retention xấu có liên quan tới chất lượng traffic hay không).\n"
                "- Bước 4: TỔNG HỢP THÔNG ĐIỆP CHÍNH: rút ra 3–5 kết luận bao quát phản ánh đúng bộ dữ liệu (tăng trưởng, rủi ro, cơ hội, vấn đề chất lượng dữ liệu). Các insight và recommendations phải chỉ rõ chúng xuất phát từ module nào (business/journey/seo/retention/cart/ml_prediction/khác). Ví dụ có thể chèn nhẹ cuối câu: '(module cart.channels)', '(module ml_prediction.overview)', '(module business.data_quality)', v.v. để người đọc biết nguồn gốc insight.\n"
                "- Trong mọi bước, hãy CHÚ Ý NHẬN XÉT VỀ CHÍNH DỮ LIỆU ĐẦU VÀO: mức độ đầy đủ, có bị lệch về thời gian/kênh, có nhiều giá trị 0/null hay không, có mâu thuẫn giữa các module (vd: sessions rất thấp nhưng revenue rất cao, hoặc ngược lại).\n"
                "1) Business KPIs (và chất lượng dữ liệu business):\n"
                "   - Phân tích mối quan hệ giữa sessions, users, orders, revenue, aov, conversion_rate.\n"
                "   - Nhận diện các hình thái: high-traffic/low-CR, low-traffic/high-CR, ARPU/AOV cao hay thấp.\n"
                "   - Nêu rõ các tỷ lệ %, giá trị tuyệt đối (vd: CR≈4.3%, AOV≈1,053.76$ nếu xuất hiện trong JSON).\n"
                "   - Nếu CR thấp nhưng traffic và AOV cao, hãy nêu khả năng tắc nghẽn ở checkout, form, pricing hoặc tracking. Đồng thời nhận xét xem dữ liệu có đủ dài và ổn định không (vd: chỉ trong vài ngày thì kết luận còn yếu).\n"
                "2) Funnel & Journey (phát hiện điểm nghẽn và bất thường):\n"
                "   - Tính tỉ lệ giữ lại và tỉ lệ rớt giữa từng cặp bước funnel liên tiếp. Nếu cần, ước tính tỷ lệ = step[i+1]/step[i]. Nhận xét khi một bước có volume rất nhỏ hoặc bằng 0 (có thể do thiếu tracking).\n"
                "   - Xác định rõ bước có drop‑off cao nhất, mô tả: từ bước nào sang bước nào, rớt bao nhiêu % và ý nghĩa kinh doanh. Nếu funnel bị đứt quãng (thiếu bước hoặc count bất thường), hãy ghi chú là dữ liệu chưa đủ tốt để kết luận chắc chắn.\n"
                "   - Dùng top_paths hoặc links để chỉ ra các hành trình phổ biến, hành vi bất thường (loop, dead‑end).\n"
                "3) Traffic & SEO (phân bổ, xu hướng, và độ tin cậy):\n"
                "   - Phân tích phân bổ traffic theo nguồn (direct, seo, social, referral, paid…). Tính hoặc ước lượng % share nếu có đủ số liệu.\n"
                "   - Nhận xét chất lượng từng kênh: nếu có CR per channel hãy so sánh; nếu không, suy luận từ hành vi (vd: social nhiều traffic nhưng ít purchase).\n"
                "   - Dựa trên trend theo ngày/giờ (traffic_trend hoặc by_date, activity_hourly) để nhận diện xu hướng tăng/giảm, seasonality. Nhận xét xem dữ liệu có ổn định hay bị một vài spike bất thường (cần cảnh báo).\n"
                "4) Activity theo thời gian (hành vi theo giờ/ngày và độ phủ dữ liệu):\n"
                "   - Sử dụng peak_day, peak_hour, top_hours, top_days và by_date để mô tả khung giờ/ngày cao điểm.\n"
                "   - Đưa ra gợi ý cụ thể: nên chạy chiến dịch marketing/email/remarketing vào khung giờ nào, ngày nào trong tuần.\n"
                "   - Nếu hoạt động bị lệch mạnh vào vài khung giờ/ngày, hãy cảnh báo rủi ro phụ thuộc vào một số time‑slot, đồng thời ghi chú nếu số ngày quan sát quá ít.\n"
                "5) Retention & churn (xu hướng và hạn chế dữ liệu):\n"
                "   - Dựa trên timeseries retention, đánh giá xu hướng giữ chân: đang cải thiện, xấu đi hay ổn định.\n"
                "   - Nêu rõ mốc gần nhất (ví dụ tháng mới nhất) và ước lượng % retained vs churned.\n"
                "   - Nếu retention rất thấp nhưng traffic lớn, cần đặt câu hỏi về chất lượng sản phẩm/onboarding. Đồng thời nhận xét xem timeseries có đủ nhiều mốc thời gian để kết luận (hay chỉ có 1–2 điểm dữ liệu).\n"
                "6) Data quality & độ tin cậy của số liệu (NHẬN XÉT CHI TIẾT VỀ ĐẦU VÀO):\n"
                "   - Dùng events_count, sessions_count, missing_values_pct, duplicate_events_pct, last_event_ts để đánh giá dữ liệu có đầy đủ và cập nhật không.\n"
                "   - Nếu có mẫu bất thường (vd: sessions=0 nhưng revenue>0; events rất ít nhưng revenue lớn), hãy ghi nhận như cảnh báo về tracking.\n"
                "   - Nếu dữ liệu chỉ phủ một khoảng thời gian rất ngắn, hãy ghi rõ hạn chế trong diễn giải.\n\n"
                "QUY TẮC TRÌNH BÀY & NHẬN XÉT NÂNG CAO:\n"
                "- EXECUTIVE SUMMARY: viết 3–6 câu, tập trung vào 3–5 insight chính nhất (vấn đề lớn, cơ hội lớn, rủi ro rõ ràng). Nếu ml_results.cart hoặc ml_results.ml_prediction tồn tại và không rỗng thì EXECUTIVE SUMMARY PHẢI đề cập rõ ràng đến tình trạng giỏ hàng (cart) và module ml_prediction ít nhất một lần, kể cả khi dữ liệu còn hạn chế. Khi đề cập cart/ml_prediction, ưu tiên kèm ÍT NHẤT 1 con số cụ thể nếu module đó có field số (vd: % bỏ giỏ, số giỏ, uplift dự đoán...). Nếu hoàn toàn không có field số thì phải ghi rõ là chưa có số liệu định lượng thay vì bịa.\n"
                "- 'insights.business': 4–8 bullet, mỗi bullet nên có số liệu cụ thể (%, số tuyệt đối, so sánh nếu có).\n"
                "- 'insights.journey': 4–8 bullet, nhấn mạnh các điểm nghẽn funnel, hành vi bất thường, kênh dẫn vào funnel hiệu quả/không hiệu quả.\n"
                "- 'insights.seo': 3–6 bullet, tập trung vào phân bổ kênh, xu hướng traffic, chất lượng traffic.\n"
                "- 'insights.retention': 3–6 bullet, phân tích chất lượng người dùng quay lại, rủi ro churn.\n"
                "- 'recommendations': 5–10 hành động ưu tiên (impact cao, cụ thể, có thể thực thi), có thể đánh dấu mức độ ưu tiên ngầm (vd: bắt đầu bằng 'Ưu tiên'). Nếu có module 'cart' hoặc 'ml_prediction' thì phải có ÍT NHẤT 1 recommendation gắn với mỗi module này, ví dụ: '(module cart.channels)', '(module ml_prediction.overview)'.\n"
                "- LUÔN ưu tiên dùng số liệu thực từ JSON (tỉ lệ %, top‑N, so sánh). KHÔNG được bịa số hoặc suy diễn vượt quá dữ liệu.\n"
                "- Nếu thiếu dữ liệu cho một phần, hãy bỏ qua phần đó hoặc ghi rõ là không đủ dữ liệu thay vì đoán.\n"
                "- Chỉ trả về JSON đúng schema trên, KHÔNG kèm thêm text ngoài JSON.")
            try:
                import json as _json

                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        f"{base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "Clickstream Dashboard",
                        },
                        json={
                            "model": "openai/gpt-oss-20b:free",
                            "messages": [
                                {"role": "system", "content": prompt},
                                {
                                    "role": "user",
                                    "content": _json.dumps(ml_results or {}, ensure_ascii=False),
                                },
                            ],
                            "response_format": {"type": "json_object"},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    content = None
                    try:
                        choices = data.get("choices") or []
                        if choices:
                            msg = choices[0].get("message") or {}
                            content = msg.get("content")
                    except Exception:
                        content = None

                    parsed = None
                    if isinstance(content, str):
                        try:
                            parsed = _json.loads(content)
                        except Exception:
                            parsed = None

                    if isinstance(parsed, dict):
                        parsed.setdefault("source", "openrouter")
                        return {"status": "ok", "parsed": parsed, "source": "openrouter"}

                    if isinstance(data, dict):
                        data.setdefault("source", "openrouter")
                        if "parsed" in data or "status" in data:
                            return data
                        return {"status": "ok", "parsed": data, "source": "openrouter"}
            except Exception as e:
                logger.exception("OpenRouter insights-ml call failed: %s", e)
        else:
            logger.info("analyze_ml_results: skipping OpenRouter, missing config (base_url=%s, key_is_none=%s)", base_url, key is None)

        # Fallback: compute concrete insights locally (no OpenRouter)
        def _num(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        business = (ml_results or {}).get("business") or {}
        journey = (ml_results or {}).get("journey") or {}
        seo = (ml_results or {}).get("seo") or {}
        retention = (ml_results or {}).get("retention") or {}

        # KPIs
        sessions = _num(business.get("total_sessions") or business.get("sessions") or 0)
        users = _num(business.get("total_users") or business.get("users") or 0)
        revenue = _num(business.get("revenue") or 0)
        cr = _num(business.get("conversion_rate") or 0)
        if sessions <= 0:
            views = _num(((seo.get("site_metrics") or {}).get("total_views")) or 0)
            if views > 0:
                sessions = views

        # Funnel + drop-offs
        funnel_steps = []  # [(name,value)]
        jf = journey.get("funnel")
        if isinstance(jf, dict) and isinstance(jf.get("steps"), list):
            for s in jf["steps"]:
                name = s.get("name") or s.get("step") or ""
                val = _num(s.get("value") or s.get("count") or 0)
                if name:
                    funnel_steps.append((name, val))
        elif isinstance(jf, dict):
            for k, v in jf.items():
                funnel_steps.append((str(k), _num(v)))

        drop_insights = []  # strings
        if len(funnel_steps) >= 2:
            for i in range(len(funnel_steps)-1):
                a, av = funnel_steps[i]
                b, bv = funnel_steps[i+1]
                rate = (1 - (bv/av)) if av > 0 else 0
                drop_insights.append((rate, f"Drop from {a} to {b}: {round(rate*100,2)}%"))
            drop_insights.sort(key=lambda x: x[0], reverse=True)
        top_drop = drop_insights[0][1] if drop_insights else None

        # Top sources
        top_sources = []
        try:
            dist = ((seo.get("sources") or {}).get("distribution")) or {}
            if isinstance(dist, dict):
                total = sum(_num(v) for v in dist.values()) or 1
                top_sources = [f"{k}: {round((_num(v)/total)*100,2)}%" for k, v in sorted(dist.items(), key=lambda kv: _num(kv[1]), reverse=True)[:5]]
        except Exception:
            top_sources = []

        # Retention quick facts
        ret_notes = []
        try:
            ts = retention.get("timeseries")
            if isinstance(ts, list) and ts:
                last = ts[-1]
                ret = _num(last.get("retained") or 0)
                ch = _num(last.get("churned") or 0)
                total = ret + ch if (ret+ch) > 0 else 1
                ret_notes.append(f"Latest retention: {round((ret/total)*100,2)}%")
        except Exception:
            pass

        # Key insights bullets
        insights = []
        if sessions:
            insights.append(f"Sessions: {int(sessions):,}")
        if users:
            insights.append(f"Users: {int(users):,}")
        if cr:
            insights.append(f"Conversion rate: {round(cr*100,2)}%")
        if revenue:
            insights.append(f"Revenue: ${round(revenue,2):,.2f}")
        if top_drop:
            insights.append(top_drop)
        if top_sources:
            insights.append("Top sources • " + "; ".join(top_sources))
        insights.extend(ret_notes)

        # Recommendations heuristics
        recs = []
        if top_drop:
            recs.append("Investigate top drop-off path; fix UX or messaging at that step")
        if top_sources:
            recs.append("Double down on top channels; A/B landing pages for weaker sources")
        if not revenue and sessions > 0 and cr == 0:
            recs.append("No conversions with traffic; verify tracking or checkout flow")

        summary_bits = []
        if sessions: summary_bits.append(f"Sessions {int(sessions):,}")
        if users: summary_bits.append(f"Users {int(users):,}")
        if cr: summary_bits.append(f"CR {round(cr*100,2)}%")
        if revenue: summary_bits.append(f"Revenue ${round(revenue,2):,.2f}")
        if top_drop: summary_bits.append(top_drop)

        parsed = {
            "executive_summary": "; ".join(summary_bits) or "No ML results available",
            "key_insights": insights or ["Insufficient data"],
            "recommendations": recs or ["Collect more data to generate actionable recommendations"],
        }
        return {"status": "ok", "parsed": parsed, "source": "local_fallback"}
    except Exception as e:
        return {"error": str(e), "insights": "Failed to generate LLM insights"}

async def generate_recommendations(user_id: str, api_key: str, db) -> Dict:
    """
    Generate personalized recommendations using OpenRouter AI
    """
    user_data = await db.events.get_user_events(user_id)
    product_data = await db.products.get_all()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OPENROUTER_API_URL}/recommend",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "user_data": user_data,
                "products": product_data
            }
        )
        response.raise_for_status()
        return response.json()

async def get_insights(user_id: str, api_key: str, db) -> Dict:
    """
    Get AI-generated insights about user behavior
    """
    user_data = await db.events.get_user_events(user_id)
    session_data = await db.events.get_user_sessions(user_id)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OPENROUTER_API_URL}/insights",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "user_data": user_data,
                "sessions": session_data
            }
        )
        response.raise_for_status()
        return response.json()