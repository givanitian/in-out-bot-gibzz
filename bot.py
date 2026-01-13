import json
import os
from datetime import datetime
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
        "➕ /in  – Pemasukan\n"
        "➖ /out – Pengeluaran\n"
        "💰 /balance – Saldo\n"
        "📜 /history – Riwayat\n"
        "⚙️ /config – Edit / Hapus\n\n"
        "Success is not final; failure is not fatal: It is the courage to continue that counts.",
        parse_mode="Markdown"
    )


# ================= IN / OUT =================
async def in_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'in'
    context.user_data['step'] = 'amount'
    await update.message.reply_text("➕ *PEMASUKAN*\n💵 Masukkan jumlah:", parse_mode="Markdown")


async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'out'
    context.user_data['step'] = 'amount'
    await update.message.reply_text("➖ *PENGELUARAN*\n💸 Masukkan jumlah:", parse_mode="Markdown")


# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    data = load_data()

    if user_id not in data:
        data[user_id] = {'transactions': []}

    # ========= MODE EDIT =========
    if 'editing' in context.user_data:
        trans_id = context.user_data['editing']
        transaction = next((t for t in data[user_id]['transactions'] if t['id'] == trans_id), None)

        if not transaction:
            context.user_data.clear()
            await update.message.reply_text("❌ Transaksi tidak ditemukan.")
            return

        if text.lower() == 'hapus':
            data[user_id]['transactions'] = [
                t for t in data[user_id]['transactions'] if t['id'] != trans_id
            ]
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("🗑️ Transaksi berhasil dihapus.")
            return

        try:
            parts = text.split()
            if len(parts) < 3:
                raise ValueError

            new_type = parts[0].lower()
            if new_type not in ['in', 'out']:
                raise ValueError

            transaction['type'] = new_type
            transaction['amount'] = float(parts[1])
            transaction['description'] = ' '.join(parts[2:])

            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Transaksi berhasil diperbarui.")
        except:
            await update.message.reply_text(
                "❌ Format salah.\n"
                "Gunakan:\n"
                "`in 10000 Gaji`\n"
                "`out 5000 Jajan`\n"
                "atau ketik *hapus*",
                parse_mode="Markdown"
            )
        return

    # ========= MODE INPUT IN / OUT =========
    if 'step' in context.user_data:
        if context.user_data['step'] == 'amount':
            try:
                context.user_data['temp_amount'] = float(text)
                context.user_data['step'] = 'description'
                await update.message.reply_text("📝 Masukkan deskripsi:")
            except ValueError:
                await update.message.reply_text("❌ Jumlah harus angka.")
            return

        if context.user_data['step'] == 'description':
            transaction = {
                'id': len(data[user_id]['transactions']) + 1,
                'type': context.user_data['mode'],
                'amount': context.user_data['temp_amount'],
                'description': text,
                'time': datetime.now().strftime("%d-%m-%Y %H:%M")
            }

            data[user_id]['transactions'].append(transaction)
            save_data(data)

            emoji = "✅" if transaction['type'] == 'in' else "📤"
            await update.message.reply_text(
                f"{emoji} *Transaksi tersimpan!*\n\n"
                f"🕒 {transaction['time']}\n"
                f"💰 {rupiah(transaction['amount'])}\n"
                f"📝 {transaction['description']}",
                parse_mode="Markdown"
            )

            context.user_data.clear()
            return


# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if not data.get(user_id, {}).get('transactions'):
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

    if not data.get(user_id, {}).get('transactions'):
        await update.message.reply_text("📭 Belum ada transaksi.")
        return

    text = "📜 *RIWAYAT TRANSAKSI*\n\n"
    for t in data[user_id]['transactions']:
        icon = "➕" if t['type'] == 'in' else "➖"
        waktu = t.get('time', '-')
        text += f"{icon} {waktu} | {rupiah(t['amount'])} | {t['description']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ================= CONFIG =================
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if not data.get(user_id, {}).get('transactions'):
        await update.message.reply_text("⚙️ Tidak ada transaksi.")
        return

    keyboard = [
        [InlineKeyboardButton(
            f"✏️ {t.get('time','-')} | {rupiah(t['amount'])}",
            callback_data=f"edit_{t['id']}"
        )]
        for t in data[user_id]['transactions']
    ]

    await update.message.reply_text(
        "⚙️ *Pilih transaksi:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ================= BUTTON =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    trans_id = int(query.data.split("_")[1])
    context.user_data.clear()
    context.user_data['editing'] = trans_id

    await query.edit_message_text(
        "✏️ *EDIT TRANSAKSI*\n\n"
        "Kirim:\n"
        "`in 10000 Gaji`\n"
        "`out 5000 Jajan`\n\n"
        "🗑️ atau ketik *hapus*",
        parse_mode="Markdown"
    )


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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()


if __name__ == '__main__':
    main()
