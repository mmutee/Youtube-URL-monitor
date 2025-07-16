import pyperclip
import subprocess
import time
import re
from threading import Thread
from collections import defaultdict

# Configuration
YT_DLP_PATH = "yt-dlp.exe"
CHECK_INTERVAL = 2
LAST_URL = None

# YouTube URL pattern
YOUTUBE_URL_PATTERN = re.compile(
    r'(https?://)?(www\.)?'
    '(youtube|youtu|youtube-nocookie)\.(com|be)/'
    '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
)

def is_youtube_url(text):
    """Check if the text contains a YouTube URL"""
    #textURL = text
    if not text or not isinstance(text, str):
        return False
    return bool(YOUTUBE_URL_PATTERN.search(text))

def parse_yt_dlp_formats(output):
    """Parse modern yt-dlp -F output into structured format"""
    formats = []
    has_original_default = False
    
    if not output:
        return formats
    
    # First check if any audio has "original (default)"
    if "original (default)" in output:
        has_original_default = True
    
    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Skip header lines and info lines
        if line.startswith(('[youtube]', 'ID', 'D    EXT', '--')) or 'RESOLUTION' in line:
            continue
        
        # Process format lines (lines starting with format code)
        if re.match(r'^\d+', line):
            try:
                # Split the line into components
                parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
                
                # Get format code (first column)
                code = parts[0].split()[0]
                
                # Determine if audio or video
                is_audio = 'audio only' in line
                
                if is_audio:
                    # Audio format parsing
                    resolution = 'audio only'
                    
                    # Find the size (look for MiB/KiB pattern)
                    size_match = re.search(r'(\d+\.?\d*\s*(MiB|KiB))', line)
                    size = size_match.group(1) if size_match else '0MiB'
                    
                    # Skip non-original audio if we have original default versions
                    if has_original_default and 'original (default)' not in line:
                        continue
                else:
                    # Video format parsing
                    # Resolution is in parts[1] (skip EXT which is parts[0].split()[1])
                    resolution = parts[1] if len(parts) > 1 else ''
                    
                    # Size is after FPS/channels (parts[3] typically)
                    size_match = re.search(r'(\d+\.?\d*\s*(MiB|KiB))', line)
                    size = size_match.group(1) if size_match else '0MiB'
                
                # Extract codec
                codec = extract_codec(line)
                
                # Create format dictionary
                fmt = {
                    'code': code,
                    'resolution': resolution,
                    'size': size,
                    'type': 'audio' if is_audio else 'video',
                    'codec': codec
                }
                    
                formats.append(fmt)
            except Exception as e:
                print("Skipping line due to error: " + line + " - " + str(e))
                continue
    return formats

def extract_codec(line):
    """Extract codec information from the line"""
    # Look for video codecs
    video_codecs = re.findall(r'(av01\.\w+|vp09\.\w+|avc1\.\w+|vp9)', line)
    if video_codecs:
        return video_codecs[0]
    
    # Look for audio codecs
    audio_codecs = re.findall(r'(opus|mp4a\.\w+)', line)
    if audio_codecs:
        return audio_codecs[0]
    
    return 'unknown'

def display_formats(formats):
    """Display formats in clean table sorted by size"""
    if not formats:
        print("No formats found - check if yt-dlp output format has changed")
        return
    
    # Sort by size (descending)
    def get_size_value(size_str):
        try:
            return float(size_str.replace('MiB', '').replace('KiB', ''))
        except:
            return 0.0
            
    formats.sort(key=lambda x: get_size_value(x['size']), reverse=True)
    
    # Group by type
    video_formats = [f for f in formats if f['type'] == 'video']
    audio_formats = [f for f in formats if f['type'] == 'audio']
    
    # Display video formats
    print("\nVIDEO FORMATS:")
    print("-" * 60)
    print("Code".ljust(8) + "Resolution".ljust(15) + "Size".ljust(12) + "Codec")
    print("-" * 60)
    for fmt in video_formats:
        print(
            fmt['code'].ljust(8) + " " +
            fmt['resolution'].ljust(15) + " " +
            fmt['size'].ljust(12) + " " +
            fmt['codec']
        )
    
    # Display audio formats
    if audio_formats:
        print("\nAUDIO FORMATS:")
        print("-" * 60)
        print("Code".ljust(8) + "Resolution".ljust(15) + "Size".ljust(12) + "Codec")
        print("-" * 60)
        for fmt in audio_formats:
            print(
                fmt['code'].ljust(8) + " " +
                fmt['resolution'].ljust(15) + " " +
                fmt['size'].ljust(12) + " " +
                fmt['codec']
            )
    #print(textURL)

def run_yt_dlp(url):
    """Run yt-dlp and process results"""
    global LAST_URL
    if not url or url == LAST_URL:
        return
    
    print("\nFound YouTube URL: " + url)
    print("Running yt-dlp -F to get available formats...")
    
    try:
        result = subprocess.run(
            [YT_DLP_PATH, "-F", url],
            capture_output=True,
            text=True,
            check=True
        )
        formats = parse_yt_dlp_formats(result.stdout)
        display_formats(formats)
        LAST_URL = url
        print("\n" + LAST_URL)
    except Exception as e:
        print("Error processing URL: " + str(e))
def monitor_clipboard():
    """Monitor clipboard for YouTube URLs"""
    print("Clipboard monitor started. Waiting for YouTube URLs...")
    print("Press Ctrl+C to exit...")
    while True:
        try:
            clipboard_text = pyperclip.paste()
            if clipboard_text and is_youtube_url(clipboard_text):
                run_yt_dlp(clipboard_text.strip())
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL)

def main():
    monitor_thread = Thread(target=monitor_clipboard, daemon=True)
    monitor_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
