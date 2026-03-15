import os
import yt_dlp
import cloudinary
import cloudinary.uploader
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

def process_youtube_link(url, progress_callback=None):
    """
    Downloads audio from a YouTube link (single or playlist),
    uploads to Cloudinary, and returns a list of song dictionaries.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'postprocessors':[{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'extract_flat': False # We need the full info to download
    }

    songs_data =[]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if progress_callback:
            progress_callback("🔍 Extracting information from YouTube...")
            
        info_dict = ydl.extract_info(url, download=True)

        # Check if it's a playlist or a single video
        entries = info_dict.get('entries',[info_dict])
        total_songs = len(entries)

        for index, entry in enumerate(entries, start=1):
            title = entry.get('title', 'Unknown Title')
            video_id = entry.get('id')
            duration = entry.get('duration', 0)
            
            if progress_callback:
                progress_callback(f"☁️ Uploading ({index}/{total_songs}): {title} to Cloudinary...")

            # The downloaded file path (yt-dlp converts to .mp3)
            file_path = f"downloads/{video_id}.mp3"
            
            # Get actual file size from the downloaded file
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            # Upload to Cloudinary (resource_type="video" is used for audio files)
            upload_result = cloudinary.uploader.upload(file_path, resource_type="video", folder="zemeromo_audio")
            audio_url = upload_result.get('secure_url')

            # Generate YouTube Thumbnail URL
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

            songs_data.append({
                "title": title,
                "audioUrl": audio_url,
                "thumbnailUrl": thumbnail_url,
                "fileSize": file_size,
                "duration": duration,
                "lyrics": "" # We will fill this later in the bot
            })

            # Clean up: delete the local file to save space
            if os.path.exists(file_path):
                os.remove(file_path)

    return songs_data