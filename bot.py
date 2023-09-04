import telebot
from deezloader import Login
import os
import shutil
import zipfile
import re
import random
import string
import rclone
import subprocess

# Replace these with your own values
bot_token = 'your not token here'
arl_token = '1becba9651e7d0a560757eabc5d595793ea4a6a46d6015514020cbb8b24b00d2a6fde3d12c16d9c5101b448c58a9db8d6a3e51500153051864d7dabad6dd928bc743f2ea75343cf7ecab8232269a3da2aef40fbd62125d39589ebd45c6217a53'
output_directory = 'downloads'  # Directory where downloads will be saved
download_quality = 'FLAC'  # Choose between FLAC, MP3_320, MP3_128

# Initialize the Deezloader login with ARL token
downloader = Login(arl=arl_token)

# Initialize the Telegram bot
bot = telebot.TeleBot(bot_token)

# Function to generate a random directory name
def generate_random_directory_name(length=10):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

# Function to sanitize a filename
def sanitize_filename(filename):
    # Remove characters that are not allowed in Windows filenames
    return re.sub(r'[\/:*?"<>|]', '', filename)

@bot.message_handler(commands=['start'])
def send_instructions(message):
    bot.send_message(message.chat.id, "Welcome to the Music Downloader bot! Send me a Deezer or Spotify track, album, or playlist link, and I'll download it for you.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        link = message.text
        chat_id = message.chat.id
        zip_filename = ''
        # Generate a random directory name for the user
        random_directory = generate_random_directory_name()
        user_output_directory = os.path.join(output_directory, random_directory)

        # Create the user's directory if it doesn't exist
        os.makedirs(user_output_directory, exist_ok=True)

        # Download the music using Deezloader
        if 'deezer.com' in link:
            if '/track/' in link:
                downloaded_tracks = downloader.download_trackdee(
                    link,
                    output_dir=user_output_directory,
                    quality_download=download_quality,
                    recursive_quality=True,
                    recursive_download=True
                )
            elif '/album/' in link:
                downloaded_tracks = downloader.download_albumdee(
                    link,
                    output_dir=user_output_directory,
                    quality_download=download_quality,
                    recursive_quality=True,
                    recursive_download=True
                )
            elif '/playlist/' in link:
                downloaded_tracks = downloader.download_playlistdee(
                    link,
                    output_dir=user_output_directory,
                    quality_download=download_quality,
                    recursive_quality=True,
                    recursive_download=True
                )
            else:
                bot.send_message(chat_id, "Unsupported link format. Please provide a valid Deezer track, album, or playlist link.")
                return
        elif 'spotify.com' in link:
            if '/track/' in link:
                downloaded_tracks = downloader.download_trackspo(
                    link,
                    output_dir=user_output_directory,
                    quality_download=download_quality,
                    recursive_quality=True,
                    recursive_download=True
                )
            elif '/album/' in link:
                downloaded_tracks = downloader.download_albumspo(
                    link,
                    output_dir=user_output_directory,
                    quality_download=download_quality,
                    recursive_quality=True,
                    recursive_download=True
                )
            elif '/playlist/' in link:
                downloaded_tracks = downloader.download_playlistspo(
                    link,
                    output_dir=user_output_directory,
                    quality_download=download_quality,
                    recursive_quality=True,
                    recursive_download=True
                )
            else:
                bot.send_message(chat_id, "Unsupported link format. Please provide a valid Spotify track, album, or playlist link.")
                return
        else:
            bot.send_message(chat_id, "Unsupported link format. Please provide a valid Deezer or Spotify link.")
            return

         # Compress the downloaded tracks into a ZIP file
        zip_filename = os.path.basename(link).replace('/', '_') + '.zip'
        zip_filename = sanitize_filename(zip_filename)  # Sanitize the filename
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(user_output_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, user_output_directory))

        # Upload the ZIP file to Google Drive using rclone
        rclone_cfg = r'C:\Users\Tony Stark\Desktop\Deezer\rclone.conf'
        remote_name = '[Tony_Drive]'
        remote_directory = '1ZJ89QrS6841EKdXqmd6cyFzviO2_ZbbE'
        remote_path = remote_name + ':' + remote_directory
        rclone_command = f'rclone copy "{zip_filename}" Tony_Drive:remote_directory'
        subprocess.run(rclone_command, shell=True, check=True)
        rc = rclone.with_config(rclone_cfg)
        result = subprocess.run(rclone_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = result.stdout.decode('utf-8')
        stderr = result.stderr.decode('utf-8')

        # Print the output for debugging purposes
        print("rclone stdout:", stdout)
        print("rclone stderr:", stderr)
        # Upload the ZIP file
        rc.sync(zip_filename, remote_path)

        # Send a message to the user indicating the successful upload
        bot.send_message(chat_id, "Music successfully uploaded to Google Drive!")

        # Clean up the user's directory and ZIP file
        shutil.rmtree(user_output_directory)
        os.remove(zip_filename)

    except Exception as e:
        bot.send_message(chat_id, f"An error occurred: {str(e)}")

        # In case of an error, remove the user's directory and ZIP file
        if os.path.exists(user_output_directory):
            shutil.rmtree(user_output_directory)
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
            
if __name__ == '__main__':
    bot.polling()

