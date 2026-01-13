import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
TOKEN = '8500413116:AAESjylyadhRiN19KDC8bUKOXY5Yo1_Kqjw'
DATA_FILE = 'user_data.json'


# ================= HELPER =================
def rupiah(amount):
    return f"Rp {amount:,.0f}".replace(",", ".")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💵 *IN & OUT GIBZZ!*\n\n"
        "📌 *Perintah:*\n"
        "➕ /in  – Catat pemasukan\n"
        "➖ /out – Catat pengeluaran\n"
        "💰 /balance – Lihat saldo\n"
        "📜 /history – Riwayat transaksi\n"
        "⚙️ /config – Edit / hapus transaksi\n\n"
        "✨ Input bertahap & otomatis Rupiah 🇮🇩",
        parse_mode="Markdown"
    )


# ================= IN / OUT =================
async def in_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'in'
    context.user_data['step'] = 'amount'
    await update.message.reply_text(
        "➕ *PEMASUKAN*\n\n💵 Masukkan *jumlah*: ",
        parse_mode="Markdown"
    )


async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'out'
    context.user_data['step'] = 'amount'
    await update.message.reply_text(
        "➖ *PENGELUARAN*\n\n💸 Masukkan *jumlah*: ",
        parse_mode="Markdown"
    )


# ================= STEP HANDLER =================
async def step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'step' not in context.user_data:
        return

    user_id = str(update.effective_user.id)
    data = load_data()
    text = update.message.text.strip()

    if user_id not in data:
        data[user_id] = {'transactions': []}

    # STEP 1 - AMOUNT
    if context.user_data['step'] == 'amount':
        try:
            amount = float(text)
            context.user_data['temp_amount'] = amount
            context.user_data['step'] = 'description'
            await update.message.reply_text(
                "📝 Masukkan *deskripsi*: ",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Jumlah harus angka!\n💡 Contoh: 50000"
            )

    # STEP 2 - DESCRIPTION
    elif context.user_data['step'] == 'description':
        transaction = {
            'id': len(data[user_id]['transactions']) + 1,
            'type': context.user_data['mode'],
            'amount': context.user_data['temp_amount'],
            'description': text
        }

        data[user_id]['transactions'].append(transaction)
        save_data(data)

        emoji = "✅" if transaction['type'] == 'in' else "📤"

        await update.message.reply_text(
            f"{emoji} *Transaksi berhasil dicatat!*\n\n"
            f"💰 Jumlah: {rupiah(transaction['amount'])}\n"
            f"📝 Deskripsi: {transaction['description']}",
            parse_mode="Markdown"
        )

        context.user_data.clear()


# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]['transactions']:
        await update.message.reply_text("📭 Belum ada transaksi.")
        return

    total_in = sum(t['amount'] for t in data[user_id]['transactions'] if t['type'] == 'in')
    total_out = sum(t['amount'] for t in data[user_id]['transactions'] if t['type'] == 'out')
    saldo = total_in - total_out

    await update.message.reply_text(
        f"💰 *SALDO SAAT INI*\n\n"
        f"➕ Pemasukan: {rupiah(total_in)}\n"
        f"➖ Pengeluaran: {rupiah(total_out)}\n"
        f"📊 Saldo: *{rupiah(saldo)}*",
        parse_mode="Markdown"
    )


# ================= HISTORY =================
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]['transactions']:
        await update.message.reply_text("📭 Belum ada transaksi.")
        return

    text = "📜 *RIWAYAT TRANSAKSI*\n\n"
    for t in data[user_id]['transactions']:
        icon = "➕" if t['type'] == 'in' else "➖"
        text += f"{icon} ID {t['id']} | {rupiah(t['amount'])} | {t['description']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ================= CONFIG =================
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]['transactions']:
        await update.message.reply_text("⚙️ Tidak ada transaksi.")
        return

    keyboard = []
    for t in data[user_id]['transactions']:
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ ID {t['id']} - {rupiah(t['amount'])}",
                callback_data=f"edit_{t['id']}"
            )
        ])

    await update.message.reply_text(
        "⚙️ *Pilih transaksi:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ================= BUTTON =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = load_data()

    if query.data.startswith("edit_"):
        trans_id = int(query.data.split("_")[1])
        transaction = next((t for t in data[user_id]['transactions'] if t['id'] == trans_id), None)

        if transaction:
            context.user_data['editing'] = trans_id
            await query.edit_message_text(
                f"✏️ *Edit Transaksi ID {trans_id}*\n\n"
                "Format:\n"
                "`in 10000 Gaji`\n"
                "`out 5000 Jajan`\n\n"
                "🗑️ Kirim *hapus* untuk menghapus",
                parse_mode="Markdown"
            )


# ================= EDIT =================
async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'editing' not in context.user_data:
        return

    user_id = str(update.effective_user.id)
    data = load_data()
    trans_id = context.user_data['editing']
    text = update.message.text.strip()

    transaction = next((t for t in data[user_id]['transactions'] if t['id'] == trans_id), None)
    if not transaction:
        return

    if text.lower() == 'hapus':
        data[user_id]['transactions'] = [t for t in data[user_id]['transactions'] if t['id'] != trans_id]
        save_data(data)
        await update.message.reply_text("🗑️ Transaksi dihapus.")
    else:
        try:
            parts = text.split()
            transaction['type'] = parts[0]
            transaction['amount'] = float(parts[1])
            transaction['description'] = ' '.join(parts[2:])
            save_data(data)
            await update.message.reply_text("✅ Transaksi diperbarui.")
        except:
            await update.message.reply_text("❌ Format salah.")

    context.user_data.clear()


# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("in", in_command))
    app.add_handler(CommandHandler("out", out_command))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("config", config))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, step_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit))

    app.run_polling()


if __name__ == '__main__':
    main()
