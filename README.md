# Zemeromo Admin Bot 🎵

**Zemeromo Admin Bot** is a private Telegram Bot used to automate content management for the Zemeromo platform. It seamlessly downloads audio from YouTube videos or playlists, uploads it to Cloudinary, and generates a structured, bulk-upload JSON payload for the Zemeromo Express backend.

## ✨ Features
- **Interactive Workflow:** Smooth, step-by-step prompts for identifying Church, Artist, and Album properties.
- **YouTube Audio Processing:** Automatically downloads YouTube videos or entire playlists and converts them to high-quality MP3 format via `yt-dlp`.
- **Thumbnail Extraction:** Automatically fetches high-resolution thumbnails via the YouTube CDN.
- **Interactive Lyrics Prompting:** Allows admins to effortlessly add lyrics for each song in a playlist directly via Telegram.
- **Automated Data Formatting:** Generates and delivers a flawlessly structured JSON document customized for the Zemeromo Bulk Import API.
- **Cloudinary Integration:** Automatically uploads processed audio files securely to Cloudinary.

## 📋 Prerequisites
Ensure the following tools are ready on your system before proceeding:
- **Python 3.10+**
- **FFmpeg & FFprobe:** Must be placed in the project root folder or set in your system environment `PATH`.
- **Node.js:** Necessary for `yt-dlp`'s JavaScript runtime executing complex YouTube extractors.

## 🛠️ Setup Instructions

### 1. Installation

Clone this repository and create a Python virtual environment:

```bash
# Set up a virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install all required dependencies
python -m pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root directory and populate it with your credentials:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMIN_TELEGRAM_ID=your_telegram_user_id
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```
*(Note: Ensure you include your exact Telegram user ID in `ADMIN_TELEGRAM_ID` to receive the bot's private administrative permissions.)*

### 3. Running the Bot

Run the following command to start the bot. It will securely launch the long-polling process:

```bash
python bot.py
```

## 🎮 Usage Guide
1. Open up **Telegram** and initiate a chat with your provisioned bot instance.
2. Send the `/start` command to trigger the step-by-step procedure.
3. **Configure Entities:** Follow the interactive prompts to declare Church, Artist, and Album parameters (either specify MongoDB IDs directly or input names).
4. **Target Context:** Paste your target **YouTube Video** or **Playlist** link. *(Note: Depending on the playlist size, processing and uploading might take a brief period).*
5. **Attach Lyrics:** Enter complete lyrics when the bot prompts you sequentially for each downloaded song, or simply type `skip` to bypass.
6. **Fetch Output:** Upon completion, the bot will deliver a newly generated **Bulk Upload `.json`** configured seamlessly for your context.
7. Upload this `.json` right into the Zemeromo Admin Panel interface!