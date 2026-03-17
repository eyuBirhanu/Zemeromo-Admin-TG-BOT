import os
import shutil
import yt_dlp
import cloudinary
import cloudinary.uploader
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

def process_youtube_link(url, progress_callback=None):
    cookie_path = 'cookies.txt' 
    
    if os.path.exists('/etc/secrets/cookies.txt'):
        shutil.copyfile('/etc/secrets/cookies.txt', cookie_path)
        print("✅ Copied cookies to writable location")
    elif not os.path.exists(cookie_path):
        print("⚠️ WARNING: cookies.txt not found! YouTube might block this.")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'ffmpeg_location': './bin',  
        'cookiefile': cookie_path, 
        'extractor_args': {
            'youtube':[
                'client=android',
                'player_skip=web'
            ]
        },
        'postprocessors':[{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'extract_flat': False
    }


    songs_data =[]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if progress_callback:
            progress_callback("🔍 Extracting information from YouTube...")
            
        info_dict = ydl.extract_info(url, download=True)

        entries = info_dict.get('entries',[info_dict])
        total_songs = len(entries)

        for index, entry in enumerate(entries, start=1):
            title = entry.get('title', 'Unknown Title')
            video_id = entry.get('id')
            duration = entry.get('duration', 0)
            
            if progress_callback:
                progress_callback(f"☁️ Uploading ({index}/{total_songs}): {title} to Cloudinary...")

            file_path = f"downloads/{video_id}.mp3"
            
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            upload_result = cloudinary.uploader.upload(file_path, resource_type="video", folder="zemeromo_audio")
            audio_url = upload_result.get('secure_url')

            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

            songs_data.append({
                "title": title,
                "audioUrl": audio_url,
                "thumbnailUrl": thumbnail_url,
                "fileSize": file_size,
                "duration": duration,
                "lyrics": ""
            })

            if os.path.exists(file_path):
                os.remove(file_path)

    return songs_data