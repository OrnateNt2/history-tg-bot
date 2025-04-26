import asyncio, textwrap
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters,
)
from config import BOT_TOKEN
from database import init_db, ensure_user
from story import load_stories, stories, get_story, Node
from state import start_or_resume_story, advance


# ─────────────── клавиатуры ───────────────
def menu_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(st.title)] for st in stories.values()],
        resize_keyboard=True
    )

def options_kb(node: Node):
    return ReplyKeyboardMarkup(
        [[KeyboardButton(opt.text)] for opt in node.options] + [[KeyboardButton("/menu")]],
        resize_keyboard=True
    )

# ─────────────── helpers ───────────────
async def show_menu(update: Update):
    await update.message.reply_text("📚 Выбери историю:", reply_markup=menu_kb())

async def send_node(chat_id: int, node: Node, ctx: ContextTypes.DEFAULT_TYPE):
    text = f"👤 *{node.text.strip()}*"
    if node.options:
        text += "\n\nВыбери действие:"
    await ctx.bot.send_message(chat_id, text, reply_markup=options_kb(node), parse_mode="Markdown")

# ─────────────── handlers ───────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update.effective_user)
    ctx.user_data.clear()
    await show_menu(update)

async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await show_menu(update)

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    uid = update.effective_user.id

    # не в истории → выбираем историю
    if "story_id" not in ctx.user_data:
        for st in stories.values():
            if msg == st.title:
                ctx.user_data["story_id"] = st.id
                story, node_id, inv, fin = await start_or_resume_story(uid, st.id)
                ctx.user_data["node_id"] = node_id
                ctx.user_data["inv"] = inv
                await send_node(uid, story.nodes[node_id], ctx)
                return
        await update.message.reply_text("Не понял. Напиши /menu")
        return

    # выход
    if msg == "/menu":
        ctx.user_data.clear()
        await show_menu(update)
        return

    # выбор опции
    story_id = ctx.user_data["story_id"]
    story = get_story(story_id)
    node = story.nodes[ctx.user_data["node_id"]]

    opt = next((o for o in node.options if o.text == msg), None)
    if not opt:
        await update.message.reply_text("Выбери кнопку действия или /menu")
        return

    next_id, err = await advance(
        uid, story_id, node.id, opt, ctx.user_data["inv"]
    )
    if err:
        await update.message.reply_text(err)
        return

    ctx.user_data["node_id"] = next_id
    next_node = story.nodes[next_id]
    await send_node(uid, next_node, ctx)

    if not next_node.options:
        await update.message.reply_text("🎉 История завершена! /menu — в меню.")
        ctx.user_data.clear()

# ─────────────── init ───────────────
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    load_stories()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()
