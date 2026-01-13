import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Ganti dengan token bot Anda dari BotFather
TOKEN = '8500413116:AAESjylyadhRiN19KDC8bUKOXY5Yo1_Kqjw'

# File untuk menyimpan data (per user)
DATA_FILE = 'user_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Selamat datang di IN & OUT GIBZZ!\n\n"
        "Perintah:\n"
        "/in <jumlah> <deskripsi> - Catat pemasukan\n"
        "/out <jumlah> <deskripsi> - Catat pengeluaran\n"
        "/balance - Lihat saldo\n"
        "/history - Lihat riwayat\n"
        "/config - Konfigurasi/edit transaksi"
    )

async def record_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, type_: str):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {'transactions': []}
    
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Format: /in <jumlah> <deskripsi> atau /out <jumlah> <deskripsi>")
            return
        amount = float(args[0])
        description = ' '.join(args[1:])
        
        transaction = {
            'id': len(data[user_id]['transactions']) + 1,
            'type': type_,
            'amount': amount,
            'description': description
        }
        data[user_id]['transactions'].append(transaction)
        save_data(data)
        await update.message.reply_text(f"Transaksi {type_} berhasil dicatat: {amount} - {description}")
    except ValueError:
        await update.message.reply_text("Jumlah harus berupa angka!")

async def in_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await record_transaction(update, context, 'in')

async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await record_transaction(update, context, 'out')

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data or not data[user_id]['transactions']:
        await update.message.reply_text("Belum ada transaksi.")
        return
    
    total_in = sum(t['amount'] for t in data[user_id]['transactions'] if t['type'] == 'in')
    total_out = sum(t['amount'] for t in data[user_id]['transactions'] if t['type'] == 'out')
    balance = total_in - total_out
    await update.message.reply_text(f"Saldo: {balance}\nPemasukan: {total_in}\nPengeluaran: {total_out}")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data or not data[user_id]['transactions']:
        await update.message.reply_text("Belum ada transaksi.")
        return
    
    history_text = "Riwayat Transaksi:\n"
    for t in data[user_id]['transactions']:
        history_text += f"ID {t['id']}: {t['type'].upper()} {t['amount']} - {t['description']}\n"
    await update.message.reply_text(history_text)

async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data or not data[user_id]['transactions']:
        await update.message.reply_text("Belum ada transaksi untuk dikonfigurasi.")
        return
    
    keyboard = []
    for t in data[user_id]['transactions']:
        keyboard.append([InlineKeyboardButton(f"Edit ID {t['id']}: {t['type'].upper()} {t['amount']}", callback_data=f"edit_{t['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih transaksi untuk edit/revisi:", reply_markup=reply_markup)

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
                f"Edit transaksi ID {trans_id}:\n"
                f"Tipe: {transaction['type']}\n"
                f"Jumlah: {transaction['amount']}\n"
                f"Deskripsi: {transaction['description']}\n\n"
                "Kirim pesan baru dalam format: <tipe> <jumlah> <deskripsi>\n"
                "Contoh: in 1000 Gaji atau out 500 Makanan\n"
                "Atau kirim 'hapus' untuk menghapus."
            )
        else:
            await query.edit_message_text("Transaksi tidak ditemukan.")

async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if 'editing' in context.user_data:
        trans_id = context.user_data['editing']
        transaction = next((t for t in data[user_id]['transactions'] if t['id'] == trans_id), None)
        if transaction:
            text = update.message.text.strip()
            if text.lower() == 'hapus':
                data[user_id]['transactions'] = [t for t in data[user_id]['transactions'] if t['id'] != trans_id]
                save_data(data)
                await update.message.reply_text(f"Transaksi ID {trans_id} dihapus.")
            else:
                try:
                    parts = text.split()
                    if len(parts) < 3:
                        await update.message.reply_text("Format salah. Gunakan: <tipe> <jumlah> <deskripsi>")
                        return
                    new_type = parts[0].lower()
                    if new_type not in ['in', 'out']:
                        await update.message.reply_text("Tipe harus 'in' atau 'out'.")
                        return
                    new_amount = float(parts[1])
                    new_desc = ' '.join(parts[2:])
                    transaction['type'] = new_type
                    transaction['amount'] = new_amount
                    transaction['description'] = new_desc
                    save_data(data)
                    await update.message.reply_text(f"Transaksi ID {trans_id} diperbarui.")
                except ValueError:
                    await update.message.reply_text("Jumlah harus angka.")
            del context.user_data['editing']
        else:
            await update.message.reply_text("Transaksi tidak ditemukan.")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("in", in_command))
    application.add_handler(CommandHandler("out", out_command))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("config", config))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit))
    
    application.run_polling()

if __name__ == '__main__':
    main()
