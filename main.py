import io
import os
import threading
import aiohttp
import discord
from discord.ext import commands
from flask import Flask

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
WELCOME_IMAGE_URL = "https://cdn.discordapp.com/attachments/1339684080224174141/1549464675647754341/Gemini_Generated_Image_p1i06up1i06up1i0.jpe?ex=6aaacaee&is=6aa9796e&hm=db15f189270f848f5170d1f11ce0c9ef13fb2c734f5b34ac78d912dc38971204"


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

    # جلب الصورة من الرابط لإرسالها كمرفق مباشر (Attachment) بدلاً من Embed
    try:
      async with aiohttp.ClientSession() as session:
        async with session.get(WELCOME_IMAGE_URL) as resp:
          if resp.status == 200:
            image_data = await resp.read()
            file = discord.File(
                fp=io.BytesIO(image_data), filename="welcome.png"
            )

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
