import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from postgrest import SyncPostgrestClient
from datetime import datetime, timedelta

# --- SETTINGS ---
API_TOKEN = '8590073276:AAGOy4GYAv01aLuA_Qzr_gxI8YZAwdLyOG4'
SUPABASE_URL = 'https://ozxueermiifhrtumnukq.supabase.co/rest/v1'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96eHVlZXJtaWlmaHJ0dW1udWtxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTUwNjIxNiwiZXhwIjoyMDg3MDgyMjE2fQ.FX5VWJHbLBUqyQZU7o_rmlAQqkaRSgGO278_3oP0B6c'
BRIDGE_URL = 'https://adanadapter-jpg.github.io/rewards/'

# The 15 Randomized Codes
VALID_CODES = [
    "WIN77", "GIFT10", "CASH99", "RIZZ5", "DRIP24", 
    "FAST44", "GOLD11", "LUX88", "BOSS01", "FIRE99",
    "MINT07", "PEAK22", "VIBE33", "GLOW55", "STAR00"
]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
db = SyncPostgrestClient(SUPABASE_URL, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args
    
    # 1. Check if user exists in your Supabase table
    res = db.table("profiles").select("*").eq("id", user_id).execute()
    
    if not res.data:
        referrer = int(args) if args and args.isdigit() else None
        db.table("profiles").insert({
            "id": user_id, 
            "balance": 0.0, 
            "referred_by": referrer, 
            "used_codes": [], 
            "last_daily": "2000-01-01T00:00:00+00:00"
        }).execute()
        
        # 2. Reward the Referrer $0.10
        if referrer:
            ref_res = db.table("profiles").select("balance").eq("id", referrer).execute()
            if ref_res.data:
                new_ref_bal = ref_res.data[0]['balance'] + 0.10
                db.table("profiles").update({"balance": new_ref_bal}).eq("id", referrer).execute()
                try: await bot.send_message(referrer, "🎊 Someone joined your link! You earned $0.10!")
                except: pass

    # 3. Get fresh user data for the dashboard
    user_data = db.table("profiles").select("*").eq("id", user_id).execute().data[0]
    
    kb = [
        [types.KeyboardButton(text="🎰 Get Task"), types.KeyboardButton(text="🎁 Daily Bonus")],
        [types.KeyboardButton(text="🏦 Balance"), types.KeyboardButton(text="💸 Withdraw")],
        [types.KeyboardButton(text="👥 My Referral Link")]
    ]
    markup = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    welcome_text = (
        f"👋 **Welcome, {message.from_user.first_name}!**\n\n"
        f"💰 **Current Balance:** ${user_data['balance']:.3f}\n"
        f"📈 **Tasks Completed:** {len(user_data.get('used_codes', []))}/15\n\n"
        f"Click 'Get Task' to earn or share your link!"
    )
    await message.answer(welcome_text, reply_markup=markup, parse_mode="Markdown")

@dp.message(lambda m: m.text == "🎰 Get Task")
async def get_task(message: types.Message):
    user_id = message.from_user.id
    res = db.table("profiles").select("used_codes").eq("id", user_id).execute()
    used = res.data[0].get('used_codes', [])
    
    # Infinite Cycle Reset: If 15 tasks done, clear list
    if len(used) >= len(VALID_CODES):
        db.table("profiles").update({"used_codes": []}).eq("id", user_id).execute()
        used = []
        await message.answer("🔄 **All tasks done! Starting a new cycle...**")

    await message.answer(f"🚀 **Task Assigned!**\n1. Visit: {BRIDGE_URL}\n2. Find the code & type it below!")

@dp.message(lambda m: m.text in VALID_CODES)
async def verify(message: types.Message):
    user_id = message.from_user.id
    res = db.table("profiles").select("balance, used_codes").eq("id", user_id).execute()
    user_data = res.data[0]
    used_codes = user_data.get('used_codes', [])
    
    if message.text in used_codes:
        await message.answer("❌ You already claimed this code in this cycle!")
        return

    used_codes.append(message.text)
    new_bal = user_data['balance'] + 0.005
    db.table("profiles").update({"balance": new_bal, "used_codes": used_codes}).eq("id", user_id).execute()
    await message.answer(f"✅ Code Accepted! +$0.005\nNew Balance: ${new_bal:.3f}")

@dp.message(lambda m: m.text == "🎁 Daily Bonus")
async def daily_bonus(message: types.Message):
    user_id = message.from_user.id
    res = db.table("profiles").select("balance, last_daily").eq("id", user_id).execute()
    data = res.data[0]
    
    # Correct timestamp parsing for Supabase
    last_daily = datetime.fromisoformat(data['last_daily'].replace('Z', '+00:00'))
    
    if datetime.now(last_daily.tzinfo) > last_daily + timedelta(hours=24):
        new_bal = data['balance'] + 0.01
        db.table("profiles").update({
            "balance": new_bal, 
            "last_daily": datetime.now().isoformat()
        }).eq("id", user_id).execute()
        await message.answer("🎁 **Daily Bonus Claimed!** +$0.01")
    else:
        await message.answer("❌ Too early! Come back in 24 hours.")

@dp.message(lambda m: m.text == "🏦 Balance")
async def check_balance(message: types.Message):
    res = db.table("profiles").select("balance").eq("id", message.from_user.id).execute()
    await message.answer(f"💳 **Your Balance:** ${res.data[0]['balance']:.3f}\nMin. Withdraw: $1.00")

@dp.message(lambda m: m.text == "💸 Withdraw")
async def withdraw(message: types.Message):
    res = db.table("profiles").select("balance").eq("id", message.from_user.id).execute()
    balance = res.data[0]['balance']
    
    if balance < 1.0:
        await message.answer(f"❌ **Withdrawal locked.** You need $1.00.\nCurrent: ${balance:.3f}")
    else:
        await message.answer("✅ **Limit reached!** Please send your payment details to the admin.")

@dp.message(lambda m: m.text == "👥 My Referral Link")
async def referral(message: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"👥 **Referral Link:**\n`{link}`\n\nEarn $0.10 for every friend who joins!")

async def main():
    print("Bot is starting... All systems active.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())