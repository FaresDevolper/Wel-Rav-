import io
import os
import threading
import aiohttp
import discord
from discord.ext import commands
from flask import Flask
from PIL import Image, ImageDraw, ImageFont

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

# معجم لتخزين الدعوات لكل سيرفر لكي نتعرف على الداعي عند انضمام عضو جديد
invites_cache = {}

# ضع ايدي روم الترحيب هنا
WELCOME_CHANNEL_ID = 1425593925414162663

# رابط صورة الترحيب
WELCOME_IMAGE_URL = "https://cdn.discordapp.com/attachments/1339684080224174141/1549888680557281330/IMG_9115.jpg?ex=6aac55d0&is=6aab0450&hm=358fbab34a0ac9c1f0764a310ef758d5e591b395d36db9e316c576759b21391a"


async def update_invites_cache():
    """تحديث كاش الدعوات لجميع السيرفرات"""
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invites_cache[guild.id] = {
                invite.code: invite.uses for invite.code in invites
            }
        except discord.Forbidden:
            print(
                "لا توجد صلاحية Manage Server لقراءة الدعوات في السيرفر:"
                f" {guild.name}"
            )
        except Exception as e:
            print(f"خطأ أثناء كاش الدعوات: {e}")


@bot.event
async def on_ready():
    print(f" تم تسجيل الدخول بنجاح باسم: {bot.user.name}")
    await update_invites_cache()


@bot.event
async def on_invite_create(invite):
    """تحديث الكاش عند إنشاء دعوة جديدة"""
    if invite.guild.id not in invites_cache:
        invites_cache[invite.guild.id] = {}
    invites_cache[invite.guild.id][invite.code] = invite.uses


@bot.event
async def on_invite_delete(invite):
    """تحديث الكاش عند حذف دعوة"""
    if invite.guild.id in invites_cache:
        invites_cache[invite.guild.id].pop(invite.code, None)


async def generate_welcome_card(background_bytes: bytes, member: discord.Member) -> io.BytesIO:
    """دالة لمعالجة الصورة ورسم صورة العضو ويوزره أسفل اليمين"""
    # فتح خلفية صورة الترحيب
    bg_image = Image.open(io.BytesIO(background_bytes)).convert("RGBA")
    
    # جلب صورة حساب العضو (Avatar)
    avatar_url = member.display_avatar.with_format("png").url
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as resp:
            avatar_bytes = await resp.read()
            
    avatar_image = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    
    # تحديد حجم صورة الحساب وتكبيرها قليلاً (مثلاً 180x180)
    avatar_size = (180, 180)
    avatar_image = avatar_image.resize(avatar_size, Image.Resampling.LANCZOS)
    
    # جعل صورة الشخص دائرية
    mask = Image.new("L", avatar_size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + avatar_size, fill=255)
    
    # وضع صورة الشخص في أسفل اليمين
    bg_w, bg_h = bg_image.size
    avatar_x = bg_w - avatar_size[0] - 80  # إزاحة من اليمين
    avatar_y = bg_h - avatar_size[1] - 120 # إزاحة من الأسفل
    
    bg_image.paste(avatar_image, (avatar_x, avatar_y), mask)
    
    # كتابة يوزر الشخص أسفل صورته
    draw = ImageDraw.Draw(bg_image)
    username = member.name
    
    # محاولة تحميل خط بحجم كبير، وفي حال عدم وجوده يتم استخدام الخط الافتراضي
    try:
        font = ImageFont.truetype("arial.ttf", 45)
    except IOError:
        font = ImageFont.load_default()

    # حساب أبعاد النص لتوسيطه أسفل الصورة
    bbox = draw.textbbox((0, 0), username, font=font)
    text_w = bbox[2] - bbox[0]
    
    text_x = avatar_x + (avatar_size[0] - text_w) // 2
    text_y = avatar_y + avatar_size[1] + 15
    
    # رسم يوزر الشخص باللون الأبيض مع تحديد أسود خفيف ليكون واضحاً
    stroke_color = (0, 0, 0)
    text_color = (255, 255, 255)
    draw.text((text_x, text_y), username, font=font, fill=text_color, stroke_width=2, stroke_fill=stroke_color)
    
    # تحويل الصورة الناتجة إلى BytesIO لإرسالها في ديسكورد
    final_buffer = io.BytesIO()
    bg_image.save(final_buffer, format="PNG")
    final_buffer.seek(0)
    return final_buffer


@bot.event
async def on_member_join(member):
    guild = member.guild
    inviter = None

    # البحث عن الرابط الذي زاد عدد استخدامه لتحديد الشخص الذي دعا العضو
    try:
        current_invites = await guild.invites()
        old_invites = invites_cache.get(guild.id, {})

        for invite in current_invites:
            old_uses = old_invites.get(invite.code, 0)
            if invite.uses > old_uses:
                inviter = invite.inviter
                old_invites[invite.code] = invite.uses
                break

        # تحديث الكاش بالكامل لضمان الدقة
        invites_cache[guild.id] = {inv.code: inv.uses for inv in current_invites}
    except Exception as e:
        print(f"تعذر تحديد الداعي: {e}")

    # تحديد روم الترحيب
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        inviter_text = inviter.mention if inviter else "غير معروف / رابط خاص"

        # رسالة الترحيب كـ Plain Text متناسق وبدون تكرار المنشن
        welcome_text = (
            f"| - **Welcome To Rav**\n\n"
            f"| - **Member** : {member.mention}\n\n"
            f"| - **Server Member** : {guild.member_count}\n\n"
            f"| - **Invited by** : {inviter_text}"
        )

        # جلب الصورة والمعالجة لإضافة الأفاتار واليوزر
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(WELCOME_IMAGE_URL) as resp:
                    if resp.status == 200:
                        bg_data = await resp.read()
                        
                        # توليد الصورة المعدلة
                        final_image = await generate_welcome_card(bg_data, member)
                        file = discord.File(fp=final_image, filename="welcome.png")

                        # إرسال الرسالة النصية مع ملف الصورة المرفق
                        await channel.send(content=welcome_text, file=file)
                    else:
                        # في حال تعذر جلب الصورة، يتم إرسال النص فقط
                        await channel.send(content=welcome_text)
        except Exception as e:
            print(f"خطأ أثناء إرسال صورة الترحيب: {e}")
            await channel.send(content=welcome_text)


# تشغيل الـ Web Server للاستضافة
keep_alive()

# تشغيل البوت (ضع التوكن الخاص بك هنا أو في Environment Variables باسم DISCORD_TOKEN)
TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot.run(TOKEN)
