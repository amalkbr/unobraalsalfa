import os
import logging
import asyncio
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
logger = logging.getLogger(__name__)

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

# متغير لمنع التكرار في الجلسة الواحدة
db_initialized = False

@app.on_event("startup")
async def on_startup():
    global db_initialized
    if not db_initialized:
        try:
            init_db()
            if run_publish_migration:
                run_publish_migration()
            db_initialized = True
            logger.info("✅ Database and migrations ready.")
        except Exception as e:
            logger.error(f"❌ Startup Error: {e}")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"📩 Incoming update: {data.get('update_id')}")
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"❌ Error handling update: {e}")
    return {"ok": True}

@app.get("/")
async def home():
    return {"status": "Bot is active", "webhook": "configured"}

@app.get("/site")
async def website():
    from fastapi.responses import HTMLResponse
    try:
        top_players = db_query("SELECT player_name, online_points FROM users ORDER BY online_points DESC LIMIT 10") or []
        rows = "".join([f"<tr><td>{i+1}</td><td>{p['player_name']}</td><td>{p['online_points']}</td></tr>" for i, p in enumerate(top_players)])
        html = f"<html><body style='text-align:center; direction:rtl;'><h1>📊 متصدري أونو</h1><table border='1' style='margin:auto;'><tr><th>#</th><th>الاسم</th><th>النقاط</th></tr>{rows}</table></body></html>"
        return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(content=f"Error: {e}")
