import os
import subprocess
import rclone
import re
import shutil
import requests
from deezloader import Login
from bson import ObjectId
from aioify import aioify
from datetime import datetime, timedelta
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import random
import string
import utils
import keys
import zipfile

# Create a MongoClient instance for your database
db_client = MongoClient(keys.db_url)
db = db_client["deezer_bot"]
links = db["links"]

# Function to generate a random directory name
def generate_random_directory_name(length=10):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

# Function to sanitize a filename
def sanitize_filename(filename):
    # Remove characters that are not allowed in Windows filenames
    return re.sub(r'[\/:*?"<>|]', '', filename)


#arl_token = '1becba9651e7d0a560757eabc5d595793ea4a6a46d6015514020cbb8b24b00d2a6fde3d12c16d9c5101b448c58a9db8d6a3e51500153051864d7dabad6dd928bc743f2ea75343cf7ecab8232269a3da2aef40fbd62125d39589ebd45c6217a53'
# Define a function to start the bot
def start_bot():
    bot = Client(
        "bot",
        api_id=keys.api_id,
        api_hash=keys.api_hash,
        bot_token=keys.bot_token
        
    )

    @bot.on_message(filters.command("start"))
    async def start_message(client, message):
        await message.reply_text("Hello")

    @bot.on_message(filters.regex(r"^https?:\/\/(?:www\.)?deezer\.com\/([a-z]*\/)?album\/(\d+)\/?$"))
    @bot.on_message(filters.regex(r"https://www.deezer.com/track/"))
    @bot.on_message(filters.regex(r"^https?:\/\/(?:www\.)?deezer\.com\/([a-z]*\/)?playlist\/(\d+)\/?$"))
    async def deezer_input(client, message):
        media_type = "playlist" if re.match(r"^https?:\/\/(?:www\.)?deezer\.com\/([a-z]*\/)?playlist\/(\d+)\/?$", message.text) else "album" if not re.search("https://www.deezer.com/track/", message.text) else "track"
        link = links.insert_one({"link": message.text, 'expire_at': datetime.utcnow() + timedelta(hours=24), 'type': media_type, 'service': 'deezer'})
        await message.reply_text("Select one of the following options:", reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Google Drive", callback_data=f"gd_{link.inserted_id}"),
                InlineKeyboardButton("Telegram", callback_data=f"tg_{link.inserted_id}")
            ]]
        ))

    @bot.on_message(filters.regex(r"^https://open.spotify.com/album"))
    @bot.on_message(filters.regex(r"^https://open.spotify.com/track"))
    @bot.on_message(filters.regex(r"^https://open.spotify.com/playlist"))
    async def spotify_input(client, message):
        media_type = 'album' if re.search(r"^https://open.spotify.com/album", message.text) else 'playlist' if re.search(r"^https://open.spotify.com/playlist", message.text) else 'track'
        link = links.insert_one({"link": message.text, 'expire_at': datetime.utcnow() + timedelta(hours=24), 'type': media_type, 'service': 'spotify'})
        await message.reply_text("Select one of the following options:\n", reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Google Drive", callback_data=f"gd_{link.inserted_id}"),
                InlineKeyboardButton("Telegram", callback_data=f"tg_{link.inserted_id}")
            ]]
        ))

    @bot.on_callback_query(filters.regex("(gd|tg)_(.+)"))
    async def handle_callback_query(client, callback_query):
        url = None
        await callback_query.message.edit("Processing...")
        link = links.find_one({"_id": ObjectId(callback_query.matches[0].group(2))})
        if link is None:
            await callback_query.answer("Timeout!", show_alert=True)
            return
        link_type = link['type']
        service = link['service']
        link = link['link']
        action = callback_query.matches[0].group(1)

        # Check if the user has already made a choice for this link
        if link not in user_choices:
            user_choices[link] = action  # Store the user's choice

            # Generate a random folder name within the "tmp" directory
            random_folder_name = generate_random_directory_name()

            # Define the directory path for downloads
            download_dir = os.path.join("tmp", random_folder_name)

            # Create the directory if it doesn't exist
            os.makedirs(download_dir, exist_ok=True)
            zip_filename = "tmp/"
            zip_file_name_only = os.path.basename(zip_filename)
            await callback_query.message.edit("Downloading...")

            # Update the download path based on the random folder name
            if service == 'deezer':
                if link_type == 'album':
                    dl = await download.download_albumdee(
                        link, output_dir=download_dir,
                        quality_download='FLAC',
                        recursive_download=True,
                        recursive_quality=True,
                        not_interface=True
                    )
                elif link_type == 'playlist':
                    dl = await download.download_playlistdee(
                        link, output_dir=download_dir,
                        quality_download='FLAC',
                        recursive_download=True,
                        recursive_quality=True,
                        not_interface=True
                    )
                elif link_type == 'track':
                    dl = await download.download_trackdee(
                        link, output_dir=download_dir,
                        quality_download='FLAC',
                        recursive_download=True,
                        recursive_quality=True,
                        not_interface=True
                    )
                    if action == 'tg':
                        await callback_query.message.reply_audio(
                            dl.song_path,
                            duration=int(utils.get_flac_duration(dl.song_path))
                        )
                        await callback_query.message.edit('Processed!')
                    else:
                        url = dl.song_path
            else:
                if link_type == 'album':
                    dl = await download.download_albumspo(
                        link, output_dir=download_dir,
                        quality_download='FLAC',
                        recursive_download=True,
                        recursive_quality=True,
                        not_interface=True
                    )
                elif link_type == 'playlist':
                    dl = await download.download_playlistspo(
                        link, output_dir=download_dir,
                        quality_download='FLAC',
                        recursive_download=True,
                        recursive_quality=True,
                        not_interface=True
                    )
                elif link_type == 'track':
                    dl = await download.download_trackspo(
                        link, output_dir=download_dir,
                        quality_download='FLAC',
                        recursive_download=True,
                        recursive_quality=True,
                        not_interface=True
                    )
                    if action == 'tg':
                        await callback_query.message.reply_audio(
                            dl.song_path,
                            duration=int(utils.get_flac_duration(dl.song_path))
                        )
                        await callback_query.message.edit('Processed!')
                    else:
                        url = dl.song_path

            await callback_query.message.edit("Creating ZIP file...")

            # Create a zip file of the downloaded folder
            zip_filename = os.path.join("tmp", random_folder_name + ".zip")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(download_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), download_dir))

            await callback_query.message.edit("Uploading ZIP file...")

            # Send the zip file to the user
            await callback_query.message.reply_document(
                document=zip_filename,
                caption="Your music files are zipped and ready for download."
            )



            if action == 'gd':  # User chose Google Drive
                # Upload the ZIP file to Google Drive using rclone
                rclone_cfg = r'C:\Users\Tony Stark\Desktop\musicbotv2-main\musicbotv2-main\rclone.conf'  # Update with your rclone config path
                remote_name = 'Tony_Drive'  # Update with your remote name
                remote_directory = '1ZJ89QrS6841EKdXqmd6cyFzviO2_ZbbE'  # Update with your remote directory
                remote_path = f"{remote_name}:{remote_directory}"
                rclone_command = f'rclone copy "{os.path.abspath(zip_filename)}" "{remote_path}"'
                subprocess.run(rclone_command, shell=True, check=True)
            
            # Clean up the temporary folder and zip file
            shutil.rmtree(download_dir)
            os.remove(zip_filename)
            
        await callback_query.message.edit("Processed!")
        # Define the base URL for the link
        base_url = "https://files.tonystarkuseless1.workers.dev/1:/remote_directory/remote_directory/"

        # Construct the link using the remote_directory and zip_filename
        link = f"{base_url}/{remote_directory}/{zip_file_name_only}"

        # Edit the message to include the link
        await callback_query.message.edit(f"Processed! You can access your file here: {link}")
    if __name__ == "__main__":
        deezloader_async = aioify(obj=Login, name='deezloader_async')
        download = deezloader_async(keys.arl_token)

        try:
            os.mkdir("tmp")
        except FileExistsError:
            pass

        links.create_index("expire_at", expireAfterSeconds=0)

        bot.run()

# Call the start_bot function to run the bot
if __name__ == "__main__":
    start_bot()
