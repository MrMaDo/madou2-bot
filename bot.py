import os
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# Conversation states
CHOOSE_MODE, CHOOSE_TOPIC, CHOOSE_STYLE, CHOOSE_DURATION, CONFIRM = range(5)

SYSTEM_NORMAL = """أنت مساعد الكاتب والشاعر المصري محمد (مادو) — صاحب 25 سنة خبرة في الشعر والغناء بالعامية المصرية.
مهمتك: كتابة سكريبتات ريلز بالعامية المصرية الأصيلة.
قواعد ثابتة:
- جمل قصيرة ومكثفة — مش فقرات طويلة
- صور حسية وواقعية بدل فلسفة مجردة
- تدفق من العاطفة للمنطق
- نهاية صامتة لا تفسر نفسها
- البنية: هوك قوي ← سيناريو واقعي بتفاصيل محددة ← الفكرة المحورية ← سطر ختامي مكثف ← CTA بسؤال ذي جانبين
- اللهجة: مصرية عامية أصيلة
- لا تبدأ بـ"أنا" أو جملة إخبارية جافة
- لا كليشيهات تطوير الذات المعلّبة
- الرد يكون السكريبت فقط بدون تقديم أو شرح"""

SYSTEM_HORROR = """أنت كاتب قصص رعب بالعامية المصرية لريلز السوشيال ميديا.
قواعد ثابتة:
- هوك مرعب في أول ثانيتين يوقف التمرير
- التفاصيل الحسية هي سلاحك (الصوت / الرائحة / البرودة / الظل)
- بناء توتر تصاعدي — مش كشف مبكر
- نهاية مفتوحة أو مقلقة أو تحذيرية
- اللهجة: مصرية عامية أصيلة
- لا مبالغة مسرحية — الواقعية أخوف من الفانتازيا
- الرد يكون السكريبت فقط بدون تقديم أو شرح"""

NORMAL_TOPICS = {
    "زوجي": "مشكلة زوجية (الصمت / التوقعات / الإهمال)",
    "مجتمع": "ضغط الأهل والمجتمع",
    "ارهاق": "إرهاق الحياة اليومية",
    "تطوير": "تطوير الذات للمتزوج",
    "روتين": "العلاقة بعد السنة الأولى",
    "صحاب": "الصحاب اللي بيتغيروا بعد الجواز",
    "قيمة": "قيمة الإنسان وسط الضغوط",
    "امراة": "المرأة المنهكة الصامتة",
    "قلب": "القلوب الطيبة اللي بتتوجع",
    "خيانة": "الخيانة والثقة المكسورة",
}

HORROR_TOPICS = {
    "نفسي": "رعب نفسي",
    "جني": "رعب جني وسحر",
    "واقعي": "رعب واقعي من البشر",
    "كابوس": "رعب كابوس",
    "منزل": "منزل أو مكان مسكون",
    "قرآني": "رعب قرآني وروحاني",
}

STYLES_NORMAL = {
    "سيناريو": "سيناريو واقعي + حكمة",
    "مونولوج": "مونولوج داخلي صادق",
    "قصة": "قصة قصيرة محكمة",
    "مقارنة": "مقارنة عاطفية (قبل / بعد)",
    "شعري": "نصيحة بأسلوب شعري",
}

STYLES_HORROR = {
    "انا": "سرد أول شخص (أنا اللي شفت)",
    "حد": "حكاية شخص قرّب يموت",
    "سمعت": "قصة سمعتها من حد قريب",
    "تحذير": "حدوتة تحذيرية",
}

user_data_store = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💡 تطوير الذات", callback_data="mode_normal")],
        [InlineKeyboardButton("👻 قصص رعب", callback_data="mode_horror")],
    ]
    await update.message.reply_text(
        "🎬 *أستوديو مادو للسكريبتات*\n\nاختار نوع المحتوى:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSE_MODE


async def choose_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    mode = query.data.replace("mode_", "")
    user_data_store[user_id] = {"mode": mode}

    if mode == "normal":
        topics = NORMAL_TOPICS
        title = "💡 اختار المحور:"
    else:
        topics = HORROR_TOPICS
        title = "👻 اختار نوع الرعب:"

    keyboard = []
    row = []
    for key, val in topics.items():
        row.append(InlineKeyboardButton(val, callback_data=f"topic_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✏️ موضوع حر", callback_data="topic_free")])

    await query.edit_message_text(title, reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSE_TOPIC


async def choose_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    topic_key = query.data.replace("topic_", "")

    if topic_key == "free":
        user_data_store[user_id]["topic_key"] = "free"
        await query.edit_message_text("✏️ اكتب موضوعك بنفسك:")
        return CHOOSE_STYLE

    mode = user_data_store[user_id]["mode"]
    topics = NORMAL_TOPICS if mode == "normal" else HORROR_TOPICS
    user_data_store[user_id]["topic"] = topics.get(topic_key, topic_key)
    user_data_store[user_id]["topic_key"] = topic_key

    return await show_styles(query, user_id)


async def handle_free_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data_store:
        await update.message.reply_text("ابدأ من الأول بـ /start")
        return ConversationHandler.END

    if user_data_store[user_id].get("waiting_for") == "duration":
        try:
            val = int(update.message.text.strip())
            val = max(15, min(180, val))
            user_data_store[user_id]["duration"] = val
            await generate_and_send(update, user_id, context)
            return CHOOSE_MODE
        except:
            await update.message.reply_text("ادخل رقم صح بالثواني (15-180)")
            return CHOOSE_DURATION

    user_data_store[user_id]["topic"] = update.message.text.strip()
    user_data_store[user_id]["topic_key"] = "free"

    class FakeQuery:
        from_user = update.message.from_user
        async def edit_message_text(self, *a, **kw):
            await update.message.reply_text(*a, **kw)
        async def answer(self): pass

    return await show_styles(FakeQuery(), user_id)


async def show_styles(query, user_id):
    mode = user_data_store[user_id]["mode"]
    styles = STYLES_NORMAL if mode == "normal" else STYLES_HORROR
    keyboard = []
    for key, val in styles.items():
        keyboard.append([InlineKeyboardButton(val, callback_data=f"style_{key}")])

    await query.edit_message_text(
        "🎨 اختار أسلوب السكريبت:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_STYLE


async def choose_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    style_key = query.data.replace("style_", "")

    mode = user_data_store[user_id]["mode"]
    styles = STYLES_NORMAL if mode == "normal" else STYLES_HORROR
    user_data_store[user_id]["style"] = styles.get(style_key, style_key)

    keyboard = [
        [
            InlineKeyboardButton("30 ث", callback_data="dur_30"),
            InlineKeyboardButton("40 ث", callback_data="dur_40"),
            InlineKeyboardButton("45 ث", callback_data="dur_45"),
        ],
        [
            InlineKeyboardButton("60 ث", callback_data="dur_60"),
            InlineKeyboardButton("90 ث", callback_data="dur_90"),
            InlineKeyboardButton("✏️ حدد بنفسك", callback_data="dur_custom"),
        ],
    ]
    await query.edit_message_text(
        "⏱ اختار مدة السكريبت:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_DURATION


async def choose_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    dur = query.data.replace("dur_", "")

    if dur == "custom":
        user_data_store[user_id]["waiting_for"] = "duration"
        await query.edit_message_text("✏️ اكتب المدة بالثواني (مثلاً: 55):")
        return CHOOSE_DURATION

    user_data_store[user_id]["duration"] = int(dur)
    user_data_store[user_id]["waiting_for"] = None

    await query.edit_message_text("⏳ بيكتب السكريبت...")
    await generate_and_send_query(query, user_id, context)
    return CHOOSE_MODE


async def generate_and_send_query(query, user_id, context):
    data = user_data_store.get(user_id, {})
    mode = data.get("mode", "normal")
    topic = data.get("topic", "")
    style = data.get("style", "")
    duration = data.get("duration", 40)
    words = round(duration * 2.5)

    system = SYSTEM_NORMAL if mode == "normal" else SYSTEM_HORROR
    prompt = f"""اكتب سكريبت {'ريلز' if mode == 'normal' else 'رعب'} عن: {topic}
الأسلوب: {style}
المدة: {duration} ثانية (ما يعادل {words} كلمة منطوقة)
اكتب السكريبت مباشرة بدون أي مقدمة."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        script = message.content[0].text
        icon = "👻" if mode == "horror" else "💡"
        reply = f"{icon} *{topic}* — {duration}ث\n\n{script}"

        keyboard = [
            [InlineKeyboardButton("🔄 غيّر لي", callback_data="regen")],
            [InlineKeyboardButton("🆕 سكريبت جديد", callback_data="new")],
        ]
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=reply,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"في مشكلة حصلت: {str(e)}"
        )


async def generate_and_send(update: Update, user_id, context):
    data = user_data_store.get(user_id, {})
    mode = data.get("mode", "normal")
    topic = data.get("topic", "")
    style = data.get("style", "")
    duration = data.get("duration", 40)
    words = round(duration * 2.5)

    system = SYSTEM_NORMAL if mode == "normal" else SYSTEM_HORROR
    prompt = f"""اكتب سكريبت {'ريلز' if mode == 'normal' else 'رعب'} عن: {topic}
الأسلوب: {style}
المدة: {duration} ثانية (ما يعادل {words} كلمة منطوقة)
اكتب السكريبت مباشرة بدون أي مقدمة."""

    await update.message.reply_text("⏳ بيكتب السكريبت...")
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        script = message.content[0].text
        icon = "👻" if mode == "horror" else "💡"
        reply = f"{icon} *{topic}* — {duration}ث\n\n{script}"

        keyboard = [
            [InlineKeyboardButton("🔄 غيّر لي", callback_data="regen")],
            [InlineKeyboardButton("🆕 سكريبت جديد", callback_data="new")],
        ]
        await update.message.reply_text(
            reply,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"في مشكلة حصلت: {str(e)}")


async def regen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ بيعيد الكتابة...")
    await generate_and_send_query(query, query.from_user.id, context)
    return CHOOSE_MODE


async def new_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💡 تطوير الذات", callback_data="mode_normal")],
        [InlineKeyboardButton("👻 قصص رعب", callback_data="mode_horror")],
    ]
    await query.edit_message_text(
        "🎬 *أستوديو مادو للسكريبتات*\n\nاختار نوع المحتوى:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSE_MODE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء. ابعت /start للبدء من جديد.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_MODE: [
                CallbackQueryHandler(choose_mode, pattern="^mode_"),
                CallbackQueryHandler(regen, pattern="^regen$"),
                CallbackQueryHandler(new_script, pattern="^new$"),
            ],
            CHOOSE_TOPIC: [
                CallbackQueryHandler(choose_topic, pattern="^topic_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_topic),
            ],
            CHOOSE_STYLE: [
                CallbackQueryHandler(choose_style, pattern="^style_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_topic),
            ],
            CHOOSE_DURATION: [
                CallbackQueryHandler(choose_duration, pattern="^dur_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_topic),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)
    print("البوت شغال...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
