#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Download ffmpeg binary manually since we are on a limited environment
mkdir -p bin
curl -L https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz | tar -xJ --strip-components=1 -C bin