import os
import logging
from fastapi import FastAPI, Request
from aiogram import Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import bot, TOKEN
from database import init_db, db_query
from handlers.admin import router as admin_router
from handlers.common import router as common_router
from handlers.reports import router as reports_router
from handlers.room_2p import router as room_2p_router
from handlers.room_multi import router as room_multi_router
from handlers.calc import router as calc_router
from handlers.stats import router as stats_router
from handlers.bara_alsalfa import router as bara_router
try:
    from handlers.community_publish import router as community_publish_router, run_publish_migration
    _use_publish_router = True
except Exception:
    community_publish_router = None
    run_publish_migration = None
    _use_publish_router = False

# تهيئة التطبيق
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# إعداد الموزع
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(admin_router)
dp.include_router(common_router)
dp.include_router(reports_router)
dp.include_router(room_2p_router)
dp.include_router(room_multi_router)
dp.include_router(calc_router)
dp.include_router(stats_router)
dp.include_router(bara_router)
if _use_publish_router:
    dp.include_router(community_publish_router)

@app.on_event("startup")
async def on_startup():
    # تهيئة قاعدة البيانات عند تشغيل السيرفر
    try:
        init_db()
        if run_publish_migration:
            run_publish_migration()
        # تعيين الويب هوك في تليجرام
        webhook_url = os.getenv("VERCEL_URL")
        if webhook_url:
            if not webhook_url.startswith("https"):
                webhook_url = f"https://{webhook_url}"
            await bot.set_webhook(f"{webhook_url}/webhook")
    except Exception as e:
        logging.error(f"Error during startup: {e}")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Error handling update: {e}")
    return {"ok": True}

@app.get("/")
async def home():
    # جلب بعض الإحصائيات لعرضها في الموقع
    stats = db_query("SELECT COUNT(*) as count FROM users")
    user_count = stats[0]['count'] if stats else 0

    rooms = db_query("SELECT COUNT(*) as count FROM rooms")
    room_count = rooms[0]['count'] if rooms else 0

    return {
        "status": "Bot is running",
        "total_users": user_count,
        "active_rooms": room_count,
        "game": "Uno & Bara Alsalfa"
    }

# واجهة بسيطة HTML (اختياري)
@app.get("/site")
async def website():
    from fastapi.responses import HTMLResponse

    # جلب أفضل اللاعبين
    top_players = db_query("SELECT player_name, online_points FROM users ORDER BY online_points DESC LIMIT 10") or []

    rows = ""
    for idx, p in enumerate(top_players):
        rows += f"<tr><td>{idx+1}</td><td>{p['player_name']}</td><td>{p['online_points']}</td></tr>"

    html_content = f"""
    <html>
        <head>
            <title>Uno Bot Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f4f4f9; text-align: center; direction: rtl; }}
                .container {{ margin-top: 50px; }}
                table {{ margin: 0 auto; border-collapse: collapse; width: 80%; background: white; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>📊 إحصائيات بوت أونو</h1>
            <div class="container">
                <h2>أفضل 10 لاعبين</h2>
                <table>
                    <tr><th>المركز</th><th>الاسم</th><th>النقاط</th></tr>
                    {rows}
                </table>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)
