import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN
from database import init_db
from story import load_stories, stories
from state import start_or_resume_story, advance, user_stories


# ──────────────────────────   helpers   ──────────────────────────
def main_menu_kb():
    # кнопки всех доступных историй
    rows = [[KeyboardButton(st.title)] for st in stories.values()]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def options_kb(node):
    # кнопки вариантов ответа
    rows = [
        [KeyboardButton(f"{idx+1}. {opt['text']}")]
        for idx, opt in enumerate(node.options)
    ]
    # добавить кнопку «/menu»
    rows.append([KeyboardButton("/menu")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def show_main_menu(update: Update):
    await update.message.reply_text(
        "📚 Выбери историю:", reply_markup=main_menu_kb()
    )


async def send_node(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    node,
):
    text = f"👤 *{node.text}*"
    if node.options:
        text += "\n\nВыбери действие:"
    await context.bot.send_message(
        chat_id, text, reply_markup=options_kb(node), parse_mode="Markdown"
    )


# ──────────────────────────   handlers   ──────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # очистить режим
    await show_main_menu(update)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_main_menu(update)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    uid = update.effective_user.id

    # 1) если не в игре — трактуем текст как название истории
    if "story_id" not in context.user_data:
        # найти историю по заголовку
        for st in stories.values():
            if msg == st.title:
                context.user_data["story_id"] = st.id
                story, node_id, inv, finished = await start_or_resume_story(
                    uid, st.id
                )
                context.user_data["node_id"] = node_id
                context.user_data["inventory"] = inv
                await send_node(uid, context, story.get_node(node_id))
                return
        await update.message.reply_text("Не понял. Используй меню /menu")
        return

    # 2) в режиме игры — обрабатываем выбор
    story_id = context.user_data["story_id"]
    story = stories[story_id]
    node = story.get_node(context.user_data["node_id"])

    # выход в меню
    if msg == "/menu":
        context.user_data.clear()
        await show_main_menu(update)
        return

    # парсим «N. текст варианта» -> N
    if not node.options:
        await update.message.reply_text("История уже окончена. /menu")
        return

    try:
        idx = int(msg.split(".")[0]) - 1
        opt = node.options[idx]
    except (ValueError, IndexError):
        await update.message.reply_text("Выбери кнопку с нужным вариантом.")
        return

    next_id = opt["next_id"]
    next_node = story.get_node(next_id)
    finished = not bool(next_node.options)

    await advance(uid, story_id, next_id, context.user_data["inventory"], finished)
    context.user_data["node_id"] = next_id

    await send_node(uid, context, next_node)

    if finished:
        await update.message.reply_text(
            "🎉 История завершена! /menu — вернуться в меню."
        )
        context.user_data.clear()


# ──────────────────────────   main   ──────────────────────────
if __name__ == "__main__":
    # отдельный цикл (Python 3.11 + PTB 20)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    load_stories()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()
