import os
import re
import time
import json
import telebot
import openai
import tempfile
import pytesseract
from telebot import types
from gtts import gTTS
from PIL import Image
from google_trans_new import google_translator
from apscheduler.schedulers.background import BackgroundScheduler

print("Current working directory:", os.getcwd())

# ====== إعداد التوكن والمفاتيح ======
TELEGRAM_BOT_TOKEN = "6669452404:AAHlWVC275ljXZaU03Yi7td9fBwruEm_PF8"
OPENAI_API_KEY = "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"

# استخدام نموذج GPT-3.5-turbo
GPT_MODEL_ID = "gpt-3.5-turbo"

# إعداد بيانات القروب للاشتراك الإجباري
GROUP_LINK = "https://t.me/NOOR200009"
GROUP_USERNAME = "@NOOR200009"

# إعداد بيانات الأدمن
ADMIN_IDS = [5545208360]  # ضع هنا رقم الـ ID الخاص بك كأدمن
ADMIN_USERNAMES = ["muneeralhu"]  # أو ضع اسم المستخدم الخاص بالأدمن (بدون @)

# تهيئة المكتبات
openai.api_key = OPENAI_API_KEY
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
translator = google_translator()

# Get bot info for referral link generation.
bot_info = bot.get_me()
bot_username = bot_info.username

# ====== ملفات JSON ======
SUBSCRIBERS_FILE = "subscribers.json"
PRO_SUBSCRIBERS_FILE = "prosubscribers.json"
BALANCE_FILE = "balances.json"  # لحفظ عداد الرسائل لكل مستخدم

# In-memory referral database: maps referral_code -> referrer's chat_id.
referral_db = {}
# To ensure that a referral is credited only once per new user.
referred_users = set()

# دوال تحميل/حفظ المشتركين
def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data)
    except:
        return set()

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(subs), f, ensure_ascii=False)

def load_pro_subscribers():
    if not os.path.exists(PRO_SUBSCRIBERS_FILE):
        return set()
    try:
        with open(PRO_SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data)
    except:
        return set()

def save_pro_subscribers(pro_subs):
    with open(PRO_SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(pro_subs), f, ensure_ascii=False)

subscribers = load_subscribers()
magical_subscribers = load_pro_subscribers()

print(f"Loaded {len(subscribers)} subscribers from {SUBSCRIBERS_FILE}")
print(f"Loaded {len(magical_subscribers)} pro subscribers from {PRO_SUBSCRIBERS_FILE}")

# ===== النظام الجديد للعداد =====
# لكل مستخدم غير مدفوع يبدأ العداد مبدئيًا من 20 رسالة (ثم الشحن اليومي 15 رسالة)
daily_recharge_amount = 15  # سيتم شحن 15 رسالة يومياً من الغد الساعة 8 مساءً

def load_balances():
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_balances(balances):
    with open(BALANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(balances, f, ensure_ascii=False)

balances = load_balances()  # المفاتيح عبارة عن chat_id كنص

admin_broadcast_mode = False
admin_adding_subscriber = False
admin_add_channel_members = False
user_modes = {}  # Stores current mode ("translate", "transliteration", "magic", "homework")

# ========== التحقق من اشتراك القروب ==========
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(GROUP_USERNAME, user_id)
        if member.status in ["left", "kicked"]:
            return False
        return True
    except:
        return False

# ========== دوال الأدمن ==========
def is_admin(user):
    if user.id in ADMIN_IDS:
        return True
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        return True
    return False

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user):
        bot.reply_to(message, "ليس لديك صلاحية الوصول.")
        return
    markup = types.InlineKeyboardMarkup()
    btn_subscribers_count = types.InlineKeyboardButton("عدد المشتركين", callback_data="subscriber_count")
    btn_broadcast = types.InlineKeyboardButton("بث رسالة", callback_data="broadcast")
    btn_add_subscriber = types.InlineKeyboardButton("Add Magical Subscriber", callback_data="add_subscriber")
    btn_add_channel = types.InlineKeyboardButton("إضافة الأعضاء من القناة", callback_data="add_from_channel")
    markup.row(btn_subscribers_count, btn_broadcast)
    markup.row(btn_add_subscriber, btn_add_channel)
    bot.send_message(message.chat.id, "🔒 لوحة الأدمن:", reply_markup=markup)

# ===== دوال خاصة بالناطق السحري =====
def send_magic_congrats(user_id):
    msg = (
        "تم اشتراكك في الناطق السحري بنجاح 🤖🌹\n"
        "نتمنى لك الفائدة والتطوير في اللغة الإنجليزية وأن تقضي وقتًا جميلًا معنا!"
    )
    bot.send_message(user_id, msg)

# ===== دوال الترجمة والتعريب =====
def get_transliteration(text):
    prompt = (
        "أرجو منك تحويل النص الإنجليزي التالي إلى عربنة صوتية باستخدام حروف عربية فقط تعبر عن النطق الفعلي لكل كلمة. "
        "لا تقم بترجمة النص، بل قم بنقل الأصوات كما تنطق باللغة الإنجليزية إلى ما يقابلها من الحروف العربية. "
        "على سبيل المثال، إذا كان النص: 'my name is sarah'، يجب أن يكون الناتج: 'ماي نيم از سارا'.\n\n"
        f"النص: {text}\n\nالعربنة:"
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3,
    )
    return response["choices"][0]["message"]["content"].strip()

# إرسال الصورة مع الكابشن الذي يحتوي على مميزات الناطق السحري
def send_magicbot_image(chat_id):
    features_text = (
        "✨ مميزات الناطق السحري:\n\n"
        "1. دقة عالية في التعريب.\n"
        "2. تعريب النصوص الطويلة بدقة.\n"
        "3. ملف صوتي احترافي للنطق.\n"
        "4. دعم الصور وتحويل النصوص منها بدقة.\n"
        "5. سرعة استجابة فائقة.\n"
        "6. دعم فني مباشر.\n"
        "7. تحديثات مستمرة.\n\n"
        "💰 الاشتراك: 30 ريال شهري\n"
        "للاشتراك تواصل مع الأستاذة نور: @Noor_teacher2"
    )
    try:
        with open("magicbot.png", "rb") as photo:
            bot.send_photo(chat_id, photo, caption=features_text)
    except Exception as e:
        bot.send_message(chat_id, f"لم يتم العثور على الصورة (magicbot.png). الخطأ: {str(e)}")

def get_gpt_voice(text):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        temp_filename = tmp.name
    tts = gTTS(text=text, lang='en')
    tts.save(temp_filename)
    return temp_filename

# Append footer shows available attempts as "available/500"
def append_footer(chat_id, response_text):
    if chat_id in magical_subscribers:
        footer = "\n----------------------------------------\nحساب مدفوع (غير محدود)"
    else:
        available = balances.get(str(chat_id), 0)
        footer = f"\n----------------------------------------\n{available}/500"
    return response_text + footer

def send_magic_response(chat_id, text):
    if chat_id not in magical_subscribers:
        bot.send_message(chat_id, "❗️ أنت غير مشترك في الناطق السحري.\nتواصل مع الأستاذة نور: @Noor_teacher2")
        return
    transliteration = get_transliteration(text)
    prompt = (
        f"Please translate the following English text to Arabic in a professional and accurate manner.\n"
        f"Text:\n{text}\n\nTranslation:"
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )
    translated = response["choices"][0]["message"]["content"].strip()
    response_text = (
        "<b>الناطق السحري:</b>\n"
        "🔹 <b>العربنة:</b>\n\n" + transliteration + "\n\n"
        "----------------------------------------\n"
        "🔹 <b>الترجمة النصية:</b>\n\n" + translated
    )
    response_text = append_footer(chat_id, response_text)
    bot.send_message(chat_id, response_text, parse_mode="HTML")
    temp_filename = get_gpt_voice(text)
    with open(temp_filename, 'rb') as audio:
        bot.send_voice(chat_id, audio)
    os.remove(temp_filename)

def send_regular_response(chat_id, text):
    transliteration = get_transliteration(text)
    response_text = "<b>التعريب:</b>\n\n" + transliteration
    response_text = append_footer(chat_id, response_text)
    bot.send_message(chat_id, response_text, parse_mode="HTML")
    tts = gTTS(text=text, lang='en')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        temp_filename = tmp.name
    tts.save(temp_filename)
    with open(temp_filename, 'rb') as audio:
        bot.send_voice(chat_id, audio)
    os.remove(temp_filename)

def send_translate_response(chat_id, text):
    prompt = (
        f"Please translate the following English text to Arabic in a professional and accurate manner.\n"
        f"Text:\n{text}\n\nTranslation:"
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )
    translated = response["choices"][0]["message"]["content"].strip()
    response_text = "<b>الترجمة:</b>\n\n" + translated
    response_text = append_footer(chat_id, response_text)
    bot.send_message(chat_id, response_text, parse_mode="HTML")

# دالة جديدة لحل الواجبات: الإجابة تكون باللون الغامق وتحتها خط.
def send_homework_response(chat_id, text):
    prompt = ("Please help me solve the following English homework problem. Provide a clear explanation and then provide the final answer in bold and underlined.\nHomework:\n" + text)
    response = openai.ChatCompletion.create(
         model="gpt-3.5-turbo",
         messages=[{"role": "user", "content": prompt}],
         max_tokens=250,
         temperature=0.3,
    )
    answer = response["choices"][0]["message"]["content"].strip()
    formatted_answer = f"<b><u>{answer}</u></b>"
    bot.send_message(chat_id, formatted_answer, parse_mode="HTML")

def process_image_and_get_text(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_path = "temp_image.jpg"
    with open(image_path, 'wb') as f:
        f.write(downloaded_file)
    try:
        extracted_text = pytesseract.image_to_string(Image.open(image_path), lang='eng')
    except Exception as e:
        extracted_text = ""
    os.remove(image_path)
    return extracted_text

# تغيير تخطيط الأزرار: كل زر يظهر في سطر منفصل.
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    btn_translate = types.KeyboardButton("الترجمة")
    btn_transliteration = types.KeyboardButton("التعريب")
    btn_magic = types.KeyboardButton("الناطق السحري")
    btn_homework = types.KeyboardButton("حل الواجبات")
    markup.row(btn_translate)
    markup.row(btn_transliteration)
    markup.row(btn_magic)
    markup.row(btn_homework)
    return markup

# /start command with referral integration.
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    parts = message.text.split()
    referral_code = parts[1] if len(parts) > 1 else None

    if not check_subscription(chat_id):
        markup = types.InlineKeyboardMarkup()
        btn_sub = types.InlineKeyboardButton("اشترك في القروب", url=GROUP_LINK)
        markup.add(btn_sub)
        bot.send_message(chat_id, "يجب الاشتراك في القروب لاستخدام البوت.", reply_markup=markup)
        return

    # Process referral if provided: إضافة 10 رسالة للمُحيل.
    if referral_code:
        referrer_chat_id = referral_db.get(referral_code)
        if referrer_chat_id and referrer_chat_id != chat_id and chat_id not in referred_users:
            balances[str(referrer_chat_id)] = balances.get(str(referrer_chat_id), 0) + 10
            save_balances(balances)
            referred_users.add(chat_id)
            bot.send_message(referrer_chat_id, "لقد حصلت على 10 رسائل إضافية بسبب إحالتك لمستخدم جديد!")
    
    # Initialize balance for non-paid users: الشحن المبدئي 20 رسالة.
    if chat_id not in magical_subscribers:
        if str(chat_id) not in balances:
            balances[str(chat_id)] = 20
            save_balances(balances)

    # Generate a referral code for the user if not exists.
    if str(chat_id) not in referral_db:
        referral_db[str(chat_id)] = chat_id
    referral_link = f"https://t.me/{bot_username}?start={str(chat_id)}"
    
    # إعداد زر الإحالة بدلاً من عرض الرابط نصاً.
    inline_kb = types.InlineKeyboardMarkup()
    btn_ref = types.InlineKeyboardButton("بوت ناطق", url=referral_link)
    inline_kb.add(btn_ref)
    
    welcome_message = "مرحبًا بك! اختر وضعك من الأزرار بالأسفل."
    bot.send_message(chat_id, welcome_message, reply_markup=get_main_keyboard())
    bot.send_message(chat_id, "شارك البوت مع أصدقائك واحصل على 10 رسائل مقابل كل شخص يدخل البوت عبر مشاركتك", reply_markup=inline_kb)

# Automatically send referral link when attempts are exhausted.
def send_referral_message(chat_id):
    referral_link = f"https://t.me/{bot_username}?start={str(chat_id)}"
    inline_kb = types.InlineKeyboardMarkup()
    btn_ref = types.InlineKeyboardButton("بوت ناطق", url=referral_link)
    inline_kb.add(btn_ref)
    message_text = (
        "لقد انتهت محاولاتك اليومية.\n"
        "يرجى إعادة شحن محاولاتك عن طريق مشاركة رابط الإحالة مع زملائك.\n"
        "شارك البوت مع أصدقائك واحصل على 10 رسائل مقابل كل شخص يدخل البوت عبر مشاركتك."
    )
    bot.send_message(chat_id, message_text, reply_markup=inline_kb)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global admin_broadcast_mode, admin_adding_subscriber, admin_add_channel_members
    chat_id = call.message.chat.id
    user = call.from_user
    data = call.data
    if not check_subscription(chat_id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القروب أولًا.", show_alert=True)
        return
    if data == "subscriber_count":
        if not is_admin(user):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
            return
        bot.send_message(chat_id, f"عدد المشتركين: {len(subscribers)}")
    elif data == "broadcast":
        if not is_admin(user):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
            return
        admin_broadcast_mode = True
        bot.send_message(chat_id, "أرسل الرسالة التي تريد بثها.")
    elif data == "add_subscriber":
        if not is_admin(user):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
            return
        admin_adding_subscriber = True
        bot.send_message(chat_id, "أعد توجيه أي رسالة من المستخدم المطلوب إضافته للناطق السحري.")
    elif data == "add_from_channel":
        if not is_admin(user):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية.", show_alert=True)
            return
        admin_add_channel_members = True
        bot.send_message(chat_id, "قم الآن بإعادة توجيه رسائل من القناة (حيث نشر الأعضاء) إلى هنا، وسأضيف مرسلي الرسائل لقائمة المشتركين.")
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    user = message.from_user
    if not check_subscription(chat_id):
        markup = types.InlineKeyboardMarkup()
        btn_sub = types.InlineKeyboardButton("اشترك في القروب", url=GROUP_LINK)
        markup.add(btn_sub)
        bot.send_message(chat_id, "يجب الاشتراك في القروب لاستخدام البوت.", reply_markup=markup)
        return
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
    
    # Mode selection: كل زر يظهر في سطر منفصل.
    if text in ["الترجمة", "التعريب", "الناطق السحري", "حل الواجبات"]:
        if text == "الترجمة":
            bot.send_message(chat_id, "يمكنك الآن إرسال نص بالإنجليزية للترجمة.")
            user_modes[chat_id] = "translate"
            return
        elif text == "التعريب":
            bot.send_message(chat_id, "يمكنك الآن إرسال نص بالإنجليزية للتعريب الصوتي.")
            user_modes[chat_id] = "transliteration"
            return
        elif text == "الناطق السحري":
            send_magicbot_image(chat_id)
            user_modes[chat_id] = "magic"
            return
        elif text == "حل الواجبات":
            if chat_id in magical_subscribers:
                bot.send_message(chat_id, "يمكنك الآن إرسال نص الواجب بالإنجليزية لحله.")
                user_modes[chat_id] = "homework"
            else:
                bot.send_message(chat_id, "لا تمتلك الاشتراك الشهري. سيتم فتح حل الواجبات مع الناطق السحري.")
                user_modes[chat_id] = "magic"
            return

    # لكل رسالة يتم خصم محاولة واحدة من العداد، إلا إذا كان المستخدم إدمن.
    if not is_admin(user) and (chat_id not in magical_subscribers):
        if str(chat_id) not in balances:
            balances[str(chat_id)] = 20
        if balances.get(str(chat_id), 0) < 1:
            bot.reply_to(message, "لقد انتهت رسائلك المتاحة. يرجى إعادة شحنها عن طريق مشاركة رابط الإحالة مع زملائك. إذا دخل أحدهم ستحصل على 10 رسائل إضافية.")
            send_referral_message(chat_id)
            return
        balances[str(chat_id)] -= 1
        save_balances(balances)
    
    if chat_id in user_modes:
        mode = user_modes[chat_id]
        if mode == "magic":
            send_magic_response(chat_id, text)
        elif mode == "transliteration":
            send_regular_response(chat_id, text)
        elif mode == "translate":
            send_translate_response(chat_id, text)
        elif mode == "homework":
            send_homework_response(chat_id, text)
        return

    if re.search(r'[\u0600-\u06FF]', text):
        bot.reply_to(message, "❗️ الرجاء إدخال النص باللغة الإنجليزية فقط.")
        return

    bot.reply_to(message, "يرجى اختيار أحد الأوضاع من الأزرار في الأسفل قبل إرسال النص.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    user = message.from_user
    if not check_subscription(chat_id):
        markup = types.InlineKeyboardMarkup()
        btn_sub = types.InlineKeyboardButton("اشترك في القروب", url=GROUP_LINK)
        markup.add(btn_sub)
        bot.send_message(chat_id, "يجب الاشتراك في القروب لاستخدام البوت.", reply_markup=markup)
        return
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
    global admin_add_channel_members
    if admin_add_channel_members and is_admin(user):
        if message.forward_from:
            old_id = message.forward_from.id
            subscribers.add(old_id)
            save_subscribers(subscribers)
            bot.send_message(chat_id, f"تمت إضافة المستخدم ID {old_id} إلى المشتركين.")
        else:
            bot.send_message(chat_id, "الرسالة ليست معاد توجيهها من مستخدم.")
        return
    if chat_id in user_modes:
        mode = user_modes[chat_id]
        extracted_text = process_image_and_get_text(message)
        if not extracted_text.strip():
            bot.reply_to(message, "لم يتم التعرف على أي نص في الصورة. يرجى المحاولة بصورة أوضح.")
            return
        if not is_admin(user) and (chat_id not in magical_subscribers):
            if str(chat_id) not in balances:
                balances[str(chat_id)] = 20
            if balances.get(str(chat_id), 0) < 1:
                bot.reply_to(message, "لقد انتهت رسائلك المتاحة. يرجى إعادة شحنها عن طريق مشاركة رابط الإحالة مع زملائك. إذا دخل أحدهم ستحصل على 10 رسائل إضافية.")
                send_referral_message(chat_id)
                return
            balances[str(chat_id)] -= 1
            save_balances(balances)
        if mode == "magic":
            send_magic_response(chat_id, extracted_text)
        elif mode == "transliteration":
            send_regular_response(chat_id, extracted_text)
        elif mode == "translate":
            send_translate_response(chat_id, extracted_text)
        elif mode == "homework":
            send_homework_response(chat_id, extracted_text)
        return
    bot.reply_to(message, "يرجى اختيار أحد الأوضاع (الترجمة، التعريب، الناطق السحري، حل الواجبات) قبل إرسال الصور.")

# دالة الشحن اليومي: تُضيف 15 رسالة لكل مستخدم عادي وتنبهه.
def daily_recharge():
    for chat_id in subscribers:
        if chat_id not in magical_subscribers:
            current = balances.get(str(chat_id), 0)
            new_val = current + daily_recharge_amount
            balances[str(chat_id)] = new_val
            try:
                bot.send_message(chat_id, f"🎁 هدية شحن: تمت إضافة 15 رسالة. رصيدك الحالي: {new_val}/500")
            except Exception as e:
                print(f"Error notifying user {chat_id}: {e}")
    save_balances(balances)
    print("Daily recharge completed.")

scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(daily_recharge, 'cron', hour=20, minute=0)
scheduler.start()

def run_bot():
    while True:
        try:
            print("Bot is polling...")
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"Bot polling error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    run_bot()
