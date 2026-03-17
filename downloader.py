import os
import shutil
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

def get_smart_paths():
    """
    Detects if running on Render or Local Windows and returns 
    the correct paths for cookies and ffmpeg.
    """
    paths = {
        'cookies': 'cookies.txt',
        'ffmpeg': '.' # Default for Windows if ffmpeg.exe is in root
    }

    # 1. Handle Cookies (Render vs Local)
    render_secrets = '/etc/secrets/cookies.txt'
    if os.path.exists(render_secrets):
        # We are on Render, copy to writable local path
        try:
            shutil.copyfile(render_secrets, 'cookies.txt')
            paths['cookies'] = 'cookies.txt'
            print("✅ Render: Cookies copied from secrets.")
        except:
            paths['cookies'] = render_secrets
    
    # 2. Handle FFmpeg (Render vs Local)
    if os.path.exists('./bin/ffmpeg'):
        # We are on Render (via build.sh)
        paths['ffmpeg'] = './bin'
        print("✅ Render: Using FFmpeg from ./bin")
    else:
        # We are on Windows
        paths['ffmpeg'] = '.' 
        print("✅ Local: Using FFmpeg from root.")

    return paths

def get_ydl_opts(is_download=True):
    """Generates standard options for yt-dlp."""
    paths = get_smart_paths()
    
    opts = {
        'quiet': True,
        'extract_flat': False,
        'cookiefile': paths['cookies'] if os.path.exists(paths['cookies']) else None,
        'no_warnings': True,
        'extractor_args': {
            'youtube': ['client=ios', 'player_skip=web'] # iOS client is harder for YT to block
        },
        # High-quality User Agent to avoid 'Sign in' error
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    }

    if is_download:
        opts.update({
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'ffmpeg_location': paths['ffmpeg'],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
    
    return opts

def process_youtube_link(url, progress_callback=None):
    """AUTOMATIC MODE: Downloads and Uploads."""
    ydl_opts = get_ydl_opts(is_download=True)
    songs_data = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if progress_callback: progress_callback("🔍 (Auto) Extracting and downloading...")
        info_dict = ydl.extract_info(url, download=True)
        entries = info_dict.get('entries', [info_dict])

        for index, entry in enumerate(entries, start=1):
            title = entry.get('title', 'Unknown Title')
            video_id = entry.get('id')
            
            if progress_callback: progress_callback(f"☁️ Uploading {index}/{len(entries)}: {title}")

            file_path = f"downloads/{video_id}.mp3"
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(file_path, resource_type="video", folder="zemeromo_audio")
            
            songs_data.append({
                "title": title,
                "audioUrl": upload_result.get('secure_url'),
                "thumbnailUrl": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                "fileSize": file_size,
                "duration": entry.get('duration', 0),
                "lyrics": ""
            })
            if os.path.exists(file_path): os.remove(file_path)

    return songs_data

def extract_metadata_only(url, progress_callback=None):
    """MANUAL MODE: Fast metadata extraction only."""
    ydl_opts = get_ydl_opts(is_download=False)
    songs_data = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if progress_callback: progress_callback("⚡ (Manual) Scraping YouTube metadata...")
        info_dict = ydl.extract_info(url, download=False) 
        entries = info_dict.get('entries', [info_dict])
        
        for entry in entries:
            songs_data.append({
                "title": entry.get('title', 'Unknown Title'),
                "audioUrl": "", 
                "thumbnailUrl": f"https://img.youtube.com/vi/{entry.get('id')}/maxresdefault.jpg",
                "fileSize": 0,  
                "duration": entry.get('duration', 0),
                "lyrics": ""    
            })
    return songs_data