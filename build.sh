#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

mkdir -p bin

if [ ! -f "bin/ffmpeg" ]; then
    echo "Downloading FFmpeg..."
    curl -L https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz | tar -xJ --strip-components=2 -C bin
fi

chmod +x bin/ffmpeg bin/ffprobe

echo "Build successful!"