import telebot
import json
import os
import re
from config import BOT_TOKEN, ADMIN_ID
from downloader import process_youtube_link
import threading
from flask import Flask
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Zemeromo Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

def is_mongo_id(string):
    """Checks if a string is a 24-character hex MongoDB ID"""
    return bool(re.match(r'^[0-9a-fA-F]{24}$', string))

@bot.message_handler(commands=['start'])
def start_process(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Unauthorized user. This bot is private.")
        return

    # Initialize empty data for this session
    user_data[message.chat.id] = {}
    
    msg = bot.reply_to(message, "Welcome to Zemeromo Bulk Uploader Bot!\n\n"
                                "Step 1: Send the **Church ID** (if it exists) OR type the **Church Name** to create a new one.")
    bot.register_next_step_handler(msg, process_church)

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    chat_id = message.chat.id
    if chat_id in user_data:
        user_data.pop(chat_id)
    bot.clear_step_handler_by_chat_id(chat_id=chat_id)
    bot.reply_to(message, "❌ Process cancelled. You can start over with /start.")


def process_church(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text.lower() == '/cancel' or text.lower() == 'cancel':
        cancel_command(message)
        return
    
    if is_mongo_id(text):
        user_data[chat_id]['churchId'] = text
        user_data[chat_id]['churchName'] = ""
    else:
        user_data[chat_id]['churchId'] = ""
        user_data[chat_id]['churchName'] = text

    msg = bot.reply_to(message, "Step 2: Send the **Artist/Choir ID** OR type the **Artist Name**.")
    bot.register_next_step_handler(msg, process_artist)

def process_artist(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text.lower() == '/cancel' or text.lower() == 'cancel':
        cancel_command(message)
        return
    
    if is_mongo_id(text):
        user_data[chat_id]['artistId'] = text
        user_data[chat_id]['artistName'] = ""
    else:
        user_data[chat_id]['artistId'] = ""
        user_data[chat_id]['artistName'] = text

    msg = bot.reply_to(message, "Step 3: Send the **Album ID** OR type the **Album Title** (Type 'skip' to use the playlist title).")
    bot.register_next_step_handler(msg, process_album)

def process_album(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text.lower() == '/cancel' or text.lower() == 'cancel':
        cancel_command(message)
        return    
    
    if text.lower() == 'skip':
        user_data[chat_id]['albumId'] = ""
        user_data[chat_id]['albumTitle'] = ""
    elif is_mongo_id(text):
        user_data[chat_id]['albumId'] = text
        user_data[chat_id]['albumTitle'] = ""
    else:
        user_data[chat_id]['albumId'] = ""
        user_data[chat_id]['albumTitle'] = text

    msg = bot.reply_to(message, "Step 4: Send the **YouTube Video or Playlist URL**:")
    bot.register_next_step_handler(msg, process_youtube)

def process_youtube(message):
    chat_id = message.chat.id
    url = message.text.strip()

    bot.send_message(chat_id, "⏳ Starting download and upload process in the background. This avoids timeouts. You can wait here...")

    def download_task():
        try:
            def send_progress(status_text):
                bot.send_message(chat_id, status_text)

            songs = process_youtube_link(url, progress_callback=send_progress)
            
            user_data[chat_id]['songs'] = songs
            
            bot.send_message(chat_id, f"✅ Successfully processed {len(songs)} songs!\n\nNow, let's add lyrics.")
            
            ask_lyrics(message, 0)

        except Exception as e:
            print(f"Error in background task: {e}")
            bot.send_message(chat_id, f"❌ Error processing YouTube link: {str(e)}")
            bot.send_message(chat_id, "Please type /start to try again.")
            
            if chat_id in user_data:
                user_data.pop(chat_id)

    thread = threading.Thread(target=download_task)
    thread.start()


def ask_lyrics(message, song_index):
    chat_id = message.chat.id
    songs = user_data[chat_id]['songs']

    if song_index >= len(songs):
        generate_final_json(message)
        return

    current_song = songs[song_index]
    msg = bot.send_message(chat_id, f"🎵 **Song {song_index + 1}/{len(songs)}: {current_song['title']}**\n\n"
                                    f"Paste the lyrics below, or type 'skip' to leave empty.", parse_mode="Markdown")
    
    bot.register_next_step_handler(msg, lambda m: save_lyrics(m, song_index))

def save_lyrics(message, song_index):
    chat_id = message.chat.id
    text = message.text.strip()

    if text.lower() != 'skip':
        user_data[chat_id]['songs'][song_index]['lyrics'] = text

    # Move to the next song
    ask_lyrics(message, song_index + 1)

def generate_final_json(message):
    chat_id = message.chat.id
    data = user_data[chat_id]

    # Structure the JSON exactly as your Express Backend expects
    album_obj = {
        "songs": data['songs']
    }
    if data['albumId']:
        album_obj['albumId'] = data['albumId']
    elif data['albumTitle']:
        album_obj['title'] = data['albumTitle']
    else:
        # If skipped and no ID, use the first song's title + " Album" as fallback
        album_obj['title'] = data['songs'][0]['title'] + " Album"

    artist_obj = {
        "albums": [album_obj]
    }
    if data['artistId']:
        artist_obj['artistId'] = data['artistId']
    if data['artistName']:
        artist_obj['name'] = data['artistName']

    church_obj = {
        "artists": [artist_obj]
    }
    if data['churchId']:
        church_obj['churchId'] = data['churchId']
    if data['churchName']:
        church_obj['name'] = data['churchName']

    final_payload = [church_obj]

    file_name = f"downloads/Zemeromo_Bulk_{chat_id}.json"
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    with open(file_name, 'rb') as doc:
        bot.send_document(chat_id, doc, caption="🎉 All done! Here is your generated JSON file ready for Bulk Upload.")

    os.remove(file_name)
    user_data.pop(chat_id, None)

if __name__ == "__main__":
    print("Starting Flask and Bot...")
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    bot.infinity_polling(timeout=60, long_polling_timeout=30)