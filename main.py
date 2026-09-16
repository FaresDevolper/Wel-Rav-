from PIL import Image, ImageDraw, ImageFont, ImageChops
import requests
import io

# دالة لتحميل الصورة من رابط
def load_image_from_url(url):
    response = requests.get(url)
    img = Image.open(io.BytesIO(response.content))
    return img

# دالة لعمل قناع دائري (circular mask)
def make_circular_mask(size):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    return mask

# --- إعدادات النص والأحجام ---
font_path = "path/to/your/font.ttf" # استبدله بمسار خط يدعم العربية، أو خط افتراضي
large_font_size = 36 # حجم خط أكبر لاسم المستخدم
small_font_size = 18 # حجم خط أصغر للنصوص الأخرى
font_color = (255, 255, 255) # أبيض
mention_color = (114, 137, 218) # لون الإشارة الافتراضي في ديسكورد

# خلفية الصورة (أسود بالكامل)
background_color = (0, 0, 0) # أسود خالص
image_size = (1000, 600) # حجم خلفية الترحيب

# --- روابط الصور (استبدلها بروابطك الفعلية) ---
user_avatar_url = "IMAGE_URL_OF_NEW_USER_AVATAR"
server_logo_url = "IMAGE_URL_OF_YOUR_SERVER_LOGO_IMAGE" # رابط الصورة التي بداخلها الشعار

# --- متغيرات نصية (للتجربة) ---
user_mention_text = "@74"
server_name = "Rav"
total_members = 254
inviter_mention = "@Fros #11"
time_text = "11:24 PM"

# --- البدء في المعالجة ---

# 1. إنشاء خلفية الترحيب السوداء
base_image = Image.new('RGB', image_size, color=background_color)
draw = ImageDraw.Draw(base_image)

# تحميل الخطوط
try:
    large_font = ImageFont.truetype(font_path, large_font_size)
    small_font = ImageFont.truetype(font_path, small_font_size)
except IOError:
    # في حال لم يجد الخط، استخدم خطاً افتراضياً
    print(f"فشل تحميل الخط من {font_path}، استخدام خط افتراضي.")
    large_font = ImageFont.load_default()
    small_font = ImageFont.load_default()

# 2. إضافة النص في الزاوية العلوية اليسرى
# ملاحظة: Pillow يرسم من اليسار إلى اليمين. قد تحتاج لتعديل المواقع للخط العربي.
current_y = 30
margin_left = 30

draw.text((margin_left, current_y), "APP", font=small_font, fill=font_color)
draw.text((margin_left + 150, current_y), time_text, font=small_font, fill=font_color)
current_y += 40

# النص: "Welcome To Rav Server" (مع تلوين Rav)
draw.text((margin_left, current_y), "Welcome To ", font=small_font, fill=font_color)
current_x = margin_left + draw.textsize("Welcome To ", font=small_font)[0]
draw.text((current_x, current_y), server_name, font=small_font, fill=font_color) # Rav بنفس اللون
# لإعطاء Rav لون مختلف: draw.text((current_x, current_y), server_name, font=small_font, fill=mention_color)
draw.text((current_x + draw.textsize(server_name, font=small_font)[0], current_y), " Server", font=small_font, fill=font_color)
current_y += 40

# النص: "Member: @74" (مع تكبير وحجم أكبر)
draw.text((margin_left, current_y), "Member : ", font=small_font, fill=font_color)
current_x = margin_left + draw.textsize("Member : ", font=small_font)[0]
draw.text((current_x, current_y), user_mention_text, font=large_font, fill=mention_color) # تكبير اسم المستخدم وتلوينه
current_y += 60 # مسافة أكبر بعد اسم المستخدم الكبير

# النص: "erver Member : 254"
# لاحظ الكلمة الأولى "erver" هي كما في الصورة، يمكنك تصحيحها هنا إلى "Server" إذا أردت.
draw.text((margin_left, current_y), f"server Member : {total_members}", font=small_font, fill=font_color)
current_y += 40

# النص: "Invited by: @Fros #11" (مع تلوين الإشارة)
draw.text((margin_left, current_y), "Invited by : ", font=small_font, fill=font_color)
current_x = margin_left + draw.textsize("Invited by : ", font=small_font)[0]
draw.text((current_x, current_y), inviter_mention, font=small_font, fill=mention_color) # تلوين الإشارة

# 3. تحميل الشعار وفصله عن خلفيته البنفسجية
print("تحميل الشعار...")
full_logo_img = load_image_from_url(server_logo_url).convert("RGBA")
# (اختياري) إذا كان الشعار كبيراً جداً، قم بتصغيره أولاً
full_logo_img.thumbnail((400, 400), Image.ANTIALIAS)

# عزل الشعار (طريقة Chroma Key مبسطة):
# سنبحث عن اللون البنفسجي (الخلفية) ونجعله شفافاً.
# هذه الطريقة تعمل بشكل جيد مع الخلفيات ذات اللون الواحد تقريباً.
print("عزل الشعار عن الخلفية البنفسجية...")
data = full_logo_img.getdata()
new_data = []
# نطاق اللون البنفسجي للبحث (قد تحتاج لتعديله)
for item in data:
    # item is (r, g, b, a)
    # البحث عن الألوان ذات اللون الأزرق العالي والأحمر المتوسط والمنخفض الأخضر (بنفسجي)
    if item[2] > 100 and item[0] < 150 and item[1] < 150:
        new_data.append((0, 0, 0, 0)) # شفاف بالكامل
    else:
        new_data.append(item)
full_logo_img.putdata(new_data)

# الآن الشعار معزول.

# 4. دمج الشعار المعزول في منتصف الخلفية السوداء
logo_x = (image_size[0] - full_logo_img.size[0]) // 2
logo_y = (image_size[1] - full_logo_img.size[1]) // 2
# الشعار المعزول يتم لصقه باستخدام نفسه كقناع شفاف
base_image.paste(full_logo_img, (logo_x, logo_y), full_logo_img)


# 5. تحميل صورة المستخدم وتحريكها للأسفل واليمين
print("تحميل صورة المستخدم...")
user_avatar_img = load_image_from_url(user_avatar_url).convert("RGBA")

# تكبير صورة المستخدم (على سبيل المثال، إلى 1.5 مرة)
user_avatar_img = user_avatar_img.resize((150, 150), Image.ANTIALIAS) # تكبير الحجم

# تحريكها إلى أسفل يمين الشعار
user_avatar_x_pos = logo_x + int(full_logo_img.size[0] * 0.7) # حرك يمين الشعار
user_avatar_y_pos = logo_y + int(full_logo_img.size[1] * 0.6) # حرك أسفل الشعار

# عمل قناع دائري لصورة المستخدم
avatar_mask = make_circular_mask(user_avatar_img.size)
user_avatar_img.putalpha(avatar_mask)

# دمج صورة المستخدم في موقعها الجديد
base_image.paste(user_avatar_img, (user_avatar_x_pos, user_avatar_y_pos), user_avatar_img)

# --- حفظ وإرسال الصورة ---
# يمكنك حفظها في ملف أو إرسالها مباشرة كـ BytesIO
print("حفظ الصورة النهائية...")
output_image_path = "welcome_final.png"
base_image.save(output_image_path)
print(f"تم حفظ الصورة بنجاح باسم {output_image_path}")

# base_image.show() # لعرض الصورة محلياً
