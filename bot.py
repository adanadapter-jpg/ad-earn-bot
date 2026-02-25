import asyncio
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from postgrest import SyncPostgrestClient
from datetime import datetime, timedelta
from aiohttp import web

# --- SETTINGS (Uses Environment Variables for Security) ---
API_TOKEN = os.getenv("API_TOKEN", "8590073276:AAGOy4GYAv01aLuA_Qzr_gxI8YZAwdLyOG4")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ozxueermiifhrtumnukq.supabase.co/rest/v1")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BRIDGE_URL = 'https://adanadapter-jpg.github.io/rewards/'

VALID_CODES = ["WIN77", "GIFT10", "CASH99", "RIZZ5", "DRIP24", "FAST44", "GOLD11", "LUX88", "BOSS01", "FIRE99", "MINT07", "PEAK22", "VIBE33", "GLOW55", "STAR00"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
db = SyncPostgrestClient(SUPABASE_URL, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})

# --- WEB SERVER FOR RENDER FREE TIER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render uses port 10000 by default for free web services
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()

# --- BOT COMMANDS ---
@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args
    res = db.table("profiles").select("*").eq("id", user_id).execute()
    
    if not res.data:
        referrer = int(args) if args and args.isdigit() else None
        db.table("profiles").insert({
            "id": user_id, "balance": 0.0, "referred_by": referrer, 
            "used_codes": [], "last_daily": "2000-01-01T00:00:00+00:00"
        }).execute()
        
        if referrer:
            ref_data = db.table("profiles").select("balance").eq("id", referrer).execute()
            if ref_data.data:
                db.table("profiles").update({"balance": ref_data.data[0]['balance'] + 0.10}).eq("id", referrer).execute()
                try: await bot.send_message(referrer, "🎊 Referral Bonus! You earned $0.10!")
                except: pass

    user_data = db.table("profiles").select("*").eq("id", user_id).execute().data[0]
    kb = [
        [types.KeyboardButton(text="🎰 Get Task"), types.KeyboardButton(text="🎁 Daily Bonus")],
        [types.KeyboardButton(text="🏦 Balance"), types.KeyboardButton(text="💸 Withdraw")],
        [types.KeyboardButton(text="👥 My Referral Link")]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(f"👋 Welcome! \n💰 Balance: ${user_data['balance']:.3f}\nInvite friends for $0.10!", reply_markup=markup)

@dp.message(lambda m: m.text == "🎰 Get Task")
async def get_task(message: types.Message):
    user_id = message.from_user.id
    res = db.table("profiles").select("used_codes").eq("id", user_id).execute()
    used = res.data[0].get('used_codes', [])
    
    if len(used) >= len(VALID_CODES):
        db.table("profiles").update({"used_codes": []}).eq("id", user_id).execute()
        await message.answer("🔄 New cycle started!")

    await message.answer(f"🚀 **Task:**\n1. Visit: {BRIDGE_URL}\n2. Enter code here!", parse_mode="Markdown")

@dp.message(lambda m: m.text == "🎁 Daily Bonus")
async def daily_bonus(message: types.Message):
    user_id = message.from_user.id
    res = db.table("profiles").select("balance, last_daily").eq("id", user_id).execute()
    data = res.data[0]
    last_daily = datetime.fromisoformat(data['last_daily'].replace('Z', '+00:00'))
    
    if datetime.now(last_daily.tzinfo) > last_daily + timedelta(hours=24):
        db.table("profiles").update({"balance": data['balance'] + 0.01, "last_daily": datetime.now().isoformat()}).eq("id", user_id).execute()
        await message.answer("🎁 Daily Reward Claimed! +$0.01")
    else:
        await message.answer("❌ Already claimed today!")

@dp.message(lambda m: m.text == "🏦 Balance")
async def check_balance(message: types.Message):
    res = db.table("profiles").select("balance").eq("id", message.from_user.id).execute()
    await message.answer(f"💳 Balance: ${res.data[0]['balance']:.3f}")

@dp.message(lambda m: m.text == "💸 Withdraw")
async def withdraw(message: types.Message):
    res = db.table("profiles").select("balance").eq("id", message.from_user.id).execute()
    if res.data[0]['balance'] < 1.0:
        await message.answer(f"❌ Min. withdraw $1.00. You have ${res.data[0]['balance']:.3f}")
    else:
        await message.answer("✅ Request sent to admin!")

@dp.message(lambda m: m.text == "👥 My Referral Link")
async def referral(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(f"📢 Share Link:\n`https://t.me/{bot_info.username}?start={message.from_user.id}`", parse_mode="Markdown")

@dp.message(lambda m: m.text in VALID_CODES)
async def verify(message: types.Message):
    user_id = message.from_user.id
    res = db.table("profiles").select("balance, used_codes").eq("id", user_id).execute()
    user_data = res.data[0]
    if message.text in user_data.get('used_codes', []):
        await message.answer("❌ Already used!")
        return
    
    used_codes = user_data.get('used_codes', [])
    used_codes.append(message.text)
    db.table("profiles").update({"balance": user_data['balance'] + 0.005, "used_codes": used_codes}).eq("id", user_id).execute()
    await message.answer(f"✅ Verified! +$0.005")

async def main():
    await start_webserver() # This keeps Render Free Tier awake
    print("Bot is starting... Web server active.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
