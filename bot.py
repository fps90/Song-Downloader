import logging
import os
import string
import random
import time
import datetime
import asyncio
import aiofiles
import aiofiles.os
import requests
import youtube_dl
from pyrogram import Client, filters
from youtube_search import YoutubeSearch
from youtubesearchpython import VideosSearch
from database import Database
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid

logging.basicConfig(level=logging.INFO)

Bot = Client(
    "Song Downloader Bot",
    bot_token=os.environ.get("BOT_TOKEN"),
    api_id=int(os.environ.get("API_ID")),
    api_hash=os.environ.get("API_HASH")
)

db = Database()

START_TEXT = """Hai {}, 
I'm a YouTube Downloader Bot. I can download Songs, Videos, and Lyrics from YouTube and upload them to Telegram. 
Use /help for more commands.
"""

HELP_TEXT = """
Here is the list of available commands and their usage:

- /song [song name or YouTube link]: Download a song.
- /lyrics [song name]: Get the lyrics of a song.
- /video [video name or YouTube link]: Download a video.

Examples:
- /song Alone
- /lyrics Alone
- /video Alone
"""

ABOUT_TEXT = """
- **Bot:** Song Downloader
- **Creator:** [MR-JINN-OF-TG](https://Github.com/MR-JINN-OF-TG)
- **Support:** [CLICK HERE](https://telegram.me/NAZRIYASUPPORT)
- **Source:** [CLICK HERE](https://github.com/MR-JINN-OF-TG/Song-Downloader)
- **Language:** Python3
- **Library:** Pyrogram
- **Server:** Heroku
"""

START_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton('Support', url="https://telegram.me/NAZRIYASUPPORT"),
            InlineKeyboardButton(text="Search", switch_inline_query_current_chat="")
        ],
        [
            InlineKeyboardButton('Help & Usage', callback_data='help'),
            InlineKeyboardButton('About', callback_data='about'),
        ]
    ]
)

HELP_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton('Home', callback_data='home'),
            InlineKeyboardButton('Close', callback_data='close')
        ]
    ]
)

ABOUT_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton('Home', callback_data='home'),
            InlineKeyboardButton('Close', callback_data='close')
        ]
    ]
)

DURATION_LIMIT = 600  # 10 minutes

is_downloading = False

@Bot.on_callback_query()
async def cb_handler(bot, update):
    query = update.data
    if query == "help":
        await update.message.edit_text(
            text=HELP_TEXT,
            reply_markup=HELP_BUTTONS,
            disable_web_page_preview=True
        )
    elif query == "about":
        await update.message.edit_text(
            text=ABOUT_TEXT,
            reply_markup=ABOUT_BUTTONS,
            disable_web_page_preview=True
        )
    else:
        await update.message.delete()

@Bot.on_message(filters.private & filters.command(["start"]))
async def start(bot, update):
    if not await db.is_user_exist(update.from_user.id):
        await db.add_user(update.from_user.id)

    await update.reply_text(
        text=START_TEXT.format(update.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=START_BUTTONS
    )

@Bot.on_message(filters.private & filters.command(["about"]))
async def about(bot, update):
    await update.reply_text(
        text=ABOUT_TEXT,
        disable_web_page_preview=True,
        reply_markup=ABOUT_BUTTONS
    )

@Bot.on_message(filters.private & filters.command("song"))
async def download_song(bot, message):
    query = ' '.join(message.command[1:])
    m = await message.reply('Searching... Please wait...')
    results = YoutubeSearch(query, max_results=1).to_dict()
    if results:
        url = f"https://youtube.com{results[0]['url_suffix']}"
        title = results[0]['title']
        await m.edit(f"Downloading {title}...")
        ydl_opts = {"format": "bestaudio"}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await m.edit(f"Uploading {title}...")
        await message.reply_audio(f"{title}.mp3")
        await m.delete()
    else:
        await m.edit("No results found.")

@Bot.on_message(filters.private & filters.command("lyrics"))
async def get_lyrics(bot, message):
    query = ' '.join(message.command[1:])
    m = await message.reply('Searching for lyrics... Please wait...')
    genius = lyricsgenius.Genius(os.environ.get("GENIUS_API_TOKEN"))
    song = genius.search_song(query)
    if song:
        await m.edit(song.lyrics)
    else:
        await m.edit("Lyrics not found.")

@Bot.on_message(filters.private & filters.command(["video"]))
async def download_video(bot, message):
    global is_downloading
    if is_downloading:
        await message.reply_text("Another download is in progress, try again after sometime.")
        return

    query = ' '.join(message.command[1:])
    m = await message.reply(f"Finding {query} on YouTube servers. Please wait...")
    search = VideosSearch(query, limit=1)
    result = search.result()["result"][0]
    video_url = result["link"]
    video_title = result["title"]
    thumb_url = result["thumbnails"][0]["url"]
    
    await asyncio.sleep(0.6)
    
    opts = {
        "format": "best",
        "outtmpl": f"{video_title}.mp4",
        "quiet": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
    }

    try:
        is_downloading = True
        with youtube_dl.YoutubeDL(opts) as ytdl:
            ytdl_data = ytdl.extract_info(video_url, download=True)
    except Exception as e:
        is_downloading = False
        await m.edit(f"Failed to download video.\nError: {str(e)}")
        return

    await m.edit("Uploading video...")
    try:
        await message.reply_video(
            f"{video_title}.mp4",
            thumb=thumb_url,
            caption=f"**Title:** [{video_title}]({video_url})",
            supports_streaming=True
        )
    except Exception as e:
        await m.edit(f"Failed to upload video.\nError: {str(e)}")
    finally:
        is_downloading = False
        await m.delete()
        for filename in [f"{video_title}.mp4", f"{video_title}.jpg"]:
            if os.path.exists(filename):
                os.remove(filename)

Bot.run()
