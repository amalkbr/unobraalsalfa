import os
import sys
import time
import base64
from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse

# 1. إعداد المسارات
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# 2. تعريف التطبيق فوراً (هذا ما يبحث عنه Vercel)
app = FastAPI()
handler = app # اسم بديل للشهرة

# 3. استيراد الموديلات بشكل "كسول" (Lazy Loading) داخل الدوال فقط
# لضمان عدم انهيار الملف أثناء التحميل الأولي

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/manifest.json")
async def manifest():
    v = int(time.time())
    return {
        "name": "أونو وبرا السالفة",
        "short_name": "السالفة",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0c29",
        "theme_color": "#6c5ce7",
        "icons": [{ "src": f"/api/app_icon.png?v={v}", "sizes": "512x512", "type": "image/png" }]
    }

# مثال لكيفية التعامل مع الـ Routers والـ Database بأمان
try:
    from domino import router as domino_router
    app.include_router(domino_router)
    from spy import router as spy_router
    app.include_router(spy_router)
except Exception as e:
    print(f"Routers could not be loaded initially: {e}")

@app.get("/api/admin/feedback")
async def get_feedback():
    try:
        from database import get_db, RealDictCursor
        with get_db() as conn:
            if not conn: return []
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 100")
                return cur.fetchall()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/feedback/delete")
async def delete_feedback(data: dict):
    try:
        from database import get_db
        with get_db() as conn:
            if not conn: return {"success": False}
            with conn.cursor() as cur:
                cur.execute("DELETE FROM feedback WHERE id = %s", (data['id'],))
                conn.commit()
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/app_icon.png")
async def get_app_icon():
    default_icon = "https://cdn-icons-png.flaticon.com/512/8030/8030198.png"
    try:
        from database import get_db_conn
        conn = get_db_conn()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM settings WHERE key = 'app_icon_data'")
                row = cur.fetchone()
                if row and row[0]:
                    return Response(content=base64.b64decode(row[0]), media_type="image/png")
    except:
        pass
    return RedirectResponse(url=default_icon)

HTML_TEMPLATE = \"\"\"
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أونو وبرا السالفة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00d2ff; --bg: #050505; --card: rgba(25, 25, 35, 0.95); --accent: #00ff88; --error: #ff2d55; }
        body { font-family: 'Cairo', sans-serif; background: #050505; color: white; margin: 0; text-align: center; }
        .card { background: var(--card); padding: 20px; border-radius: 20px; margin: 20px auto; max-width: 500px; border: 1px solid rgba(0,210,255,0.3); }
        button { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer; width: 100%; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>أونو وبرا السالفة</h1>
        <p>التطبيق يعمل الآن بنجاح على Vercel</p>
        <button onclick="alert('تم بنجاح')">اختبار</button>
    </div>
</body>
</html>
\"\"\"
