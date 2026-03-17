import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json, os, re, threading
from flask import Flask
from config import BOT_TOKEN, ADMIN_ID
from downloader import process_youtube_link, extract_metadata_only

# --- RENDER FLASK SETUP ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "Zemeromo Bot is running!", 200

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# --- BOT SETUP ---
bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def is_mongo_id(string):
    return bool(re.match(r'^[0-9a-fA-F]{24}$', string))

def check_cancel(message):
    if message.text and message.text.lower() in ['/cancel', 'cancel']:
        chat_id = message.chat.id
        user_data.pop(chat_id, None)
        bot.clear_step_handler_by_chat_id(chat_id)
        bot.send_message(chat_id, "Process cancelled. Use /start to begin again.")
        return True
    return False

# --- STEP 1: CHURCH ---
@bot.message_handler(commands=['start'])
def start_process(message):
    if message.from_user.id != ADMIN_ID: return
    user_data[message.chat.id] = {}
    msg = bot.send_message(message.chat.id, "Step 1: Send the Church ID OR type the Church Name.")
    bot.register_next_step_handler(msg, process_church)

def process_church(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    text = message.text.strip()
    if is_mongo_id(text):
        user_data[chat_id]['churchId'], user_data[chat_id]['churchName'] = text, ""
    else:
        user_data[chat_id]['churchId'], user_data[chat_id]['churchName'] = "", text
    msg = bot.send_message(chat_id, "Step 2: Send the Artist ID OR type the Artist Name.")
    bot.register_next_step_handler(msg, process_artist)

# --- STEP 2: ARTIST ---
def process_artist(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    text = message.text.strip()
    if is_mongo_id(text):
        user_data[chat_id]['artistId'], user_data[chat_id]['artistName'] = text, ""
    else:
        user_data[chat_id]['artistId'], user_data[chat_id]['artistName'] = "", text
    msg = bot.send_message(chat_id, "Step 3: Send the Album ID OR type the Album Title (type 'skip' to use playlist title).")
    bot.register_next_step_handler(msg, process_album)

# --- STEP 3: ALBUM & MODE SELECTION ---
def process_album(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    text = message.text.strip()
    user_data[chat_id]['albumId'] = text if is_mongo_id(text) else ""
    user_data[chat_id]['albumTitle'] = "" if is_mongo_id(text) or text.lower() == 'skip' else text

    # CREATING THE 3 BUTTONS
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 Automatic (YT Download)", callback_data="mode_auto"))
    markup.row(InlineKeyboardButton("✍️ YT Manual (YT Scrape)", callback_data="mode_manual"))
    markup.row(InlineKeyboardButton("📝 Full Manual (No YouTube)", callback_data="mode_full"))
    
    bot.send_message(chat_id, "Step 4: Choose your process mode:", reply_markup=markup)

# --- STEP 4: ROUTING THE MODE ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def handle_mode(call):
    chat_id = call.message.chat.id
    mode = call.data.split("_")[1]
    user_data[chat_id]['mode'] = mode
    
    bot.edit_message_text(f"Selected: {mode.upper()} Mode", chat_id, call.message.message_id)
    
    if mode == 'full':
        # FULL MANUAL ROUTE
        msg = bot.send_message(chat_id, "Step 5: How many songs are in this album?")
        bot.register_next_step_handler(msg, process_full_manual_count)
    else:
        # YOUTUBE ROUTES
        msg = bot.send_message(chat_id, "Step 5: Send the YouTube URL:")
        bot.register_next_step_handler(msg, process_youtube)

# --- YOUTUBE PROCESSING (AUTO & YT MANUAL) ---
def process_youtube(message):
    if check_cancel(message): return
    chat_id, url = message.chat.id, message.text.strip()
    mode = user_data[chat_id].get('mode', 'auto')
    bot.send_message(chat_id, "⏳ Processing YouTube link...")

    def task():
        try:
            if mode == 'auto':
                songs = process_youtube_link(url, lambda t: bot.send_message(chat_id, t))
                user_data[chat_id]['songs'] = songs
                ask_auto_lyrics(message, 0)
            else:
                songs = extract_metadata_only(url, lambda t: bot.send_message(chat_id, t))
                user_data[chat_id]['songs'] = songs
                start_manual_yt_entry(message, 0)
        except Exception as e:
            bot.send_message(chat_id, f"Error: {e}. Type /start to reset.")
    threading.Thread(target=task).start()

# --- FULL MANUAL PROCESSING (NO YOUTUBE) ---
def process_full_manual_count(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    if not message.text.isdigit():
        msg = bot.reply_to(message, "Please enter a valid number.")
        return bot.register_next_step_handler(msg, process_full_manual_count)
    
    user_data[chat_id]['songs'] = []
    user_data[chat_id]['total_manual'] = int(message.text)
    start_full_manual_loop(message, 0)

def start_full_manual_loop(message, idx):
    chat_id = message.chat.id
    total = user_data[chat_id]['total_manual']
    if idx >= total: return generate_final_json(message)
    msg = bot.send_message(chat_id, f"Song {idx+1}/{total}: Enter the Song Title:")
    bot.register_next_step_handler(msg, lambda m: save_full_manual_title(m, idx))

def save_full_manual_title(message, idx):
    if check_cancel(message): return
    user_data[message.chat.id]['songs'].append({"title": message.text.strip()})
    msg = bot.send_message(message.chat.id, "Paste the Cloudinary Audio URL:")
    bot.register_next_step_handler(msg, lambda m: save_full_manual_audio(m, idx))

def save_full_manual_audio(message, idx):
    if check_cancel(message): return
    user_data[message.chat.id]['songs'][idx]['audioUrl'] = message.text.strip()
    msg = bot.send_message(message.chat.id, "Paste the Thumbnail URL OR the YouTube Video ID:")
    bot.register_next_step_handler(msg, lambda m: save_full_manual_thumb(m, idx))

def save_full_manual_thumb(message, idx):
    if check_cancel(message): return
    text = message.text.strip()
    # Smart Thumbnail Detection
    thumb = text if "://" in text else f"https://img.youtube.com/vi/{text}/maxresdefault.jpg"
    user_data[message.chat.id]['songs'][idx]['thumbnailUrl'] = thumb
    
    msg = bot.send_message(message.chat.id, f"Thumbnail set. Enter Duration in seconds (e.g. 240):")
    bot.register_next_step_handler(msg, lambda m: save_full_manual_duration(m, idx))

def save_full_manual_duration(message, idx):
    if check_cancel(message): return
    user_data[message.chat.id]['songs'][idx]['duration'] = int(message.text) if message.text.isdigit() else 0
    msg = bot.send_message(message.chat.id, "Enter File Size in bytes (or 0):")
    bot.register_next_step_handler(msg, lambda m: save_full_manual_size(m, idx))

def save_full_manual_size(message, idx):
    if check_cancel(message): return
    user_data[message.chat.id]['songs'][idx]['fileSize'] = int(message.text) if message.text.isdigit() else 0
    msg = bot.send_message(message.chat.id, "Paste Lyrics (or 'skip'):")
    bot.register_next_step_handler(msg, lambda m: save_full_manual_lyrics(m, idx))

def save_full_manual_lyrics(message, idx):
    if check_cancel(message): return
    user_data[message.chat.id]['songs'][idx]['lyrics'] = "" if message.text.lower() == 'skip' else message.text
    start_full_manual_loop(message, idx + 1)

# --- YT MANUAL LOOP (WITH METADATA) ---
def start_manual_yt_entry(message, idx):
    songs = user_data[message.chat.id]['songs']
    if idx >= len(songs): return generate_final_json(message)
    msg = bot.send_message(message.chat.id, f"Song {idx+1}: {songs[idx]['title']}\nPaste Cloudinary Audio URL:")
    bot.register_next_step_handler(msg, lambda m: save_manual_yt_audio(m, idx))

def save_manual_yt_audio(message, idx):
    if check_cancel(message): return
    user_data[message.chat.id]['songs'][idx]['audioUrl'] = message.text.strip()
    msg = bot.send_message(message.chat.id, "Enter File Size in bytes (or 0):")
    bot.register_next_step_handler(msg, lambda m: save_manual_yt_size(m, idx))

def save_manual_yt_size(message, idx):
    if check_cancel(message): return
    user_data[message.chat.id]['songs'][idx]['fileSize'] = int(message.text) if message.text.isdigit() else 0
    msg = bot.send_message(message.chat.id, "Paste Lyrics (or 'skip'):")
    bot.register_next_step_handler(msg, lambda m: save_manual_yt_lyrics(m, idx))

def save_manual_yt_lyrics(message, idx):
    if check_cancel(message): return
    if message.text.lower() != 'skip': user_data[message.chat.id]['songs'][idx]['lyrics'] = message.text
    start_manual_yt_entry(message, idx + 1)

# --- AUTO MODE LYRICS ---
def ask_auto_lyrics(message, idx):
    songs = user_data[message.chat.id]['songs']
    if idx >= len(songs): return generate_final_json(message)
    msg = bot.send_message(message.chat.id, f"Lyrics for {songs[idx]['title']}? (type 'skip')")
    bot.register_next_step_handler(msg, lambda m: save_auto_lyrics(m, idx))

def save_auto_lyrics(message, idx):
    if check_cancel(message): return
    if message.text.lower() != 'skip': user_data[message.chat.id]['songs'][idx]['lyrics'] = message.text
    ask_auto_lyrics(message, idx + 1)

# --- FINAL GENERATION ---
def generate_final_json(message):
    chat_id = message.chat.id
    d = user_data[chat_id]
    album = {"songs": d['songs']}
    if d['albumId']: album["albumId"] = d['albumId']
    else: album["title"] = d['albumTitle'] or (d['songs'][0]['title'] + " Album")

    artist = {"albums": [album]}
    if d['artistId']: artist["artistId"] = d['artistId']
    else: artist["name"] = d['artistName']

    church = {"artists": [artist]}
    if d['churchId']: church["churchId"] = d['churchId']
    else: church["name"] = d['churchName']

    file_path = f"Zemeromo_Bulk_{chat_id}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump([church], f, indent=2, ensure_ascii=False)
    with open(file_path, 'rb') as f:
        bot.send_document(chat_id, f, caption="Done! Here is your JSON.")
    os.remove(file_path)
    user_data.pop(chat_id, None)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(timeout=60, long_polling_timeout=30)