#!/bin/bash
# Script to install FFmpeg

echo "Installing FFmpeg..."
apt-get update
apt-get install -y ffmpeg

echo "FFmpeg installed successfully!"
ffmpeg -version 