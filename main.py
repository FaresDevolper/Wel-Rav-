import io
import os
import threading
import aiohttp
import discord
from discord.ext import commands
from flask import Flask
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- سيرفر Flask لضمان استمرار عمل البوت على Render ---
app = Flask("")

@app.route("/")
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- إعدادات البوت والـ Intents ---
intents = discord.Intents.default()
intents.members = True
intents.invites = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# معجم لتخزين الدعوات لكل سيرفر
invites_cache = {}

# ايدي روم الترحيب
WELCOME_CHANNEL_ID = 1425593925414162663

# رابط الشعار الخاص بسيرفر RAV
WELCOME_LOGO_URL = "https://cdn.discordapp.com/attachments/1339684080224174141/1549874904080580648/IMG_9116.jpg?ex=6aac48fc&is=6aaaf77c&hm=41f918fb211d875e421b483beceab7537102a36ff8fcad7d1ab7cc84a1f06302"


async def generate_welcome_card(logo_bytes: bytes, avatar_bytes: bytes, username: str) -> io.BytesIO:
    """
    دالة توليد صورة الترحيب: تدمج الشعار مع صورة العضو واسمه بشكل شفاف ونقي.
    """
    # فتح صورة الشعار وصورة العضو
    logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

    # تغيير حجم صورة العضو وتفريغها في دائرة
    avatar_size = (180, 180)
    avatar_img = avatar_img.resize(avatar_size, Image.Resampling.LANCZOS)
    
    mask = Image.new("L", avatar_size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, avatar_size[0], avatar_size[1]), fill=255)
    
    avatar_circular = Image.new("RGBA", avatar_size, (0, 0, 0, 0))
    avatar_circular.paste(avatar_img, (0, 0), mask=mask)

    # تجهيز لوحة القماش (Canvas) بحجم الشعار أو إضافة مساحة متناسقة
    base_w, base_h = logo_img.size
    
    # دمج صورة العضو في منتصف/فوق الشعار
    avatar_x = (base_w - avatar_size[0]) // 2
    avatar_y = int(base_h * 0.15) # تحديد الارتفاع المناسب فوق الشعار
    
    logo_img.paste(avatar_circular, (avatar_x, avatar_y), avatar_circular)

    # كتابة اسم العضو أسفل صورة العضو
    draw = ImageDraw.Draw(logo_img)
    try:
        font = ImageFont.truetype("arial.ttf", 35)
    except IOError:
        font = ImageFont.load_default()

    text = f"@{username}"
    # حساب أبعاد النص لتوسطه
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (base_w - text_w) // 2
    text_y = avatar_y + avatar_size[1] + 15

    # رسم النص باللون الأبيض مع تحديد خفيف
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

    # حفظ الصورة في بايتات الذاكرة
    output_buffer = io.BytesIO()
    logo_img.save(output_buffer, format="PNG")
    output_buffer.seek(0)
    return output_buffer


async def update_invites_cache():
    """تحديث كاش الدعوات لجميع السيرفرات"""
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invites_cache[guild.id] = {invite.code: invite.uses for invite.code in invites}
        except discord.Forbidden:
            print(f"لا توجد صلاحية Manage Server لقراءة الدعوات في السيرفر: {guild.name}")
        except Exception as e:
            print(f"خطأ أثناء كاش الدعوات: {e}")


@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user.name}")
    await update_invites_cache()


@bot.event
async def on_invite_create(invite):
    if invite.guild.id not in invites_cache:
        invites_cache[invite.guild.id] = {}
    invites_cache[invite.guild.id][invite.code] = invite.uses


@bot.event
async def on_invite_delete(invite):
    if invite.guild.id in invites_cache:
        invites_cache[invite.guild.id].pop(invite.code, None)


@bot.event
async def on_member_join(member):
    guild = member.guild
    inviter = None

    # تحديد الشخص الذي دعا العضو
    try:
        current_invites = await guild.invites()
        old_invites = invites_cache.get(guild.id, {})

        for invite in current_invites:
            old_uses = old_invites.get(invite.code, 0)
            if invite.uses > old_uses:
                inviter = invite.inviter
                old_invites[invite.code] = invite.uses
                break

        invites_cache[guild.id] = {inv.code: inv.uses for inv in current_invites}
    except Exception as e:
        print(f"تعذر تحديد الداعي: {e}")

    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        inviter_text = inviter.mention if inviter else "غير معروف / رابط خاص"

        # نص الترحيب
        welcome_text = (
            f"| - **Welcome To Rav**\n\n"
            f"| - **Member** : {member.mention}\n\n"
            f"| - **Server Member** : {guild.member_count}\n\n"
            f"| - **Invited by** : {inviter_text}"
        )

        try:
            async with aiohttp.ClientSession() as session:
                # جلب الشعار
                async with session.get(WELCOME_LOGO_URL) as resp_logo:
                    logo_bytes = await resp_logo.read()
                
                # جلب صورة العضو الشخصية
                avatar_url = member.display_avatar.url
                async with session.get(avatar_url) as resp_avatar:
                    avatar_bytes = await resp_avatar.read()

                # دمج الصورة والشعار واسم العضو
                card_buffer = await generate_welcome_card(logo_bytes, avatar_bytes, member.name)
                file = discord.File(fp=card_buffer, filename="welcome_logo.png")

                # إرسال النص مع شعار الترحيب المدمج
                await channel.send(content=welcome_text, file=file)

        except Exception as e:
            print(f"خطأ أثناء معالجة صورة الترحيب: {e}")
            await channel.send(content=welcome_text)


# تشغيل الـ Web Server للاستضافة
keep_alive()

# تشغيل البوت
TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot.run(TOKEN)
