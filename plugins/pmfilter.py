from utils import get_random_mix_id, get_size, is_subscribed, is_req_subscribed, group_setting_buttons, get_poster, get_posterx, temp, get_settings, save_group_settings, get_cap, imdb, is_check_admin, extract_request_content, log_error, clean_filename, generate_season_variations, clean_search_text
import time
import hashlib
from rapidfuzz import process
from moviebot.util.file_properties import get_name, get_hash
from urllib.parse import quote_plus
import logging
from database.ia_filterdb import Media, Media2, get_file_details, get_search_results, get_bad_files
from database.config_db import mdb
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, ChatAdminRequired, UserNotParticipant
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, WebAppInfo
from info import *
from Script import script
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from database.refer import referdb
from database.users_chats_db import db
import asyncio
import re
import math
import random
import pytz
from datetime import datetime, timedelta
lock = asyncio.Lock()

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


DELETE_LIMIT = 100
ACTIVE_DELETE = set()


TIMEZONE = "Asia/Kolkata"
SPELL_CHECK = {}


CACHE = {}
MAX_CACHE = 100
CACHE_TTL = 300
USER_COOLDOWN = {}

@Client.on_message(filters.private & filters.incoming)
async def fsub_pool_msg_handler(client, message):
    if message.from_user.id in temp.SETTING_POOL:
        grp_id = temp.SETTING_POOL.pop(message.from_user.id)
        text = message.text
        pool = [x.strip() for x in text.split(",") if x.strip()]
        if not pool:
            await message.reply_text("Invalid input!")
            return
        
        valid_pool = []
        for ch in pool:
            try:
                await client.get_chat(ch)
                valid_pool.append(ch)
            except:
                continue
        
        if not valid_pool:
            await message.reply_text("❌ None of the provided channels/usernames are valid or accessible by the bot.")
            return

        await save_group_settings(grp_id, "fsub_pool", valid_pool)
        await save_group_settings(grp_id, "fsub_index", 0)
        await save_group_settings(grp_id, "fsub_count", 0)
        
        # Set the first one as active
        if valid_pool:
            await save_group_settings(grp_id, "fsub", [valid_pool[0]])
            
        await message.reply_text(f"✅ ꜰꜱᴜʙ ᴘᴏᴏʟ ᴜᴘᴅᴀᴛᴇᴅ ᴡɪᴛʜ {len(valid_pool)} ᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟꜱ.\nꜰꜱᴜʙ ʀᴏᴛᴀᴛɪᴏɴ ʀᴇꜱᴇᴛ.")
        return

async def _schedule_delete(sent, message, delay):
    if len(ACTIVE_DELETE) > DELETE_LIMIT:
        return
    
    task = asyncio.current_task()
    ACTIVE_DELETE.add(task)
    
    await asyncio.sleep(delay)
    try:
        await sent.delete()
        await message.delete()
    except:
        pass
    finally:
        ACTIVE_DELETE.discard(task)

def clean_cache():
    now = time.time()
    # Remove expired
    expired = [k for k, v in CACHE.items() if now - v.get("time", 0) > CACHE_TTL]
    for k in expired:
        del CACHE[k]
    # Prune if over limit
    if len(CACHE) > MAX_CACHE:
        sorted_keys = sorted(CACHE.keys(), key=lambda k: CACHE[k].get("time", 0))
        for k in sorted_keys[:len(CACHE) - MAX_CACHE]:
            del CACHE[k]
    # Clean cooldowns older than 10s
    expired_cool = [k for k, v in USER_COOLDOWN.items() if now - v > 10]
    for k in expired_cool:
        del USER_COOLDOWN[k]

def get_titles(files):
    titles = set()
    for f in files:
        t = getattr(f, "title", None)
        if t:
            titles.add(t.title())
    return sorted(list(titles))

def build_title_buttons(query_key, files):
    cache_entry = CACHE.get(query_key)
    if not cache_entry:
        return []
    titles = cache_entry["titles"]
    btn_list = []
    for i, t in enumerate(titles):
        btn_list.append(InlineKeyboardButton(t, callback_data=f"select_title|{query_key}|{i}"))
    btns = chunk_buttons(btn_list, 3)
    btns.insert(0, [InlineKeyboardButton("⇊ Sᴇʟᴇᴄᴛ Sʜᴏᴡ / Mᴏᴠɪᴇ ⇊", callback_data="ident")])
    btns.append([InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ 🚫", callback_data="close_data")])
    return btns

def get_seasons(files):
    seasons = set()
    for f in files:
        s = getattr(f, "season", None)
        if s:
            seasons.add(str(s))
    return sorted(list(seasons), key=lambda x: int(x) if str(x).isdigit() else x)

def get_languages(files, season=None):
    languages = set()
    for f in files:
        f_season = str(getattr(f, "season", ""))
        if season and season != "all" and f_season != season:
            continue
        l = getattr(f, "language", None)
        if l:
            languages.add(str(l).lower())
    return sorted(list(languages))

def get_qualities(files, season=None, language=None):
    qualities = set()
    for f in files:
        f_season = str(getattr(f, "season", ""))
        if season and season != "all" and f_season != season:
            continue
        f_lang = str(getattr(f, "language", "")).lower()
        if language and language != "all" and f_lang != language:
            continue
        q = getattr(f, "quality", None)
        if q:
            qualities.add(str(q).lower())
    return sorted(list(qualities))

def chunk_buttons(buttons, row_len=3):
    return [buttons[i:i + row_len] for i in range(0, len(buttons), row_len)]

def build_type_buttons(query_key):
    return [
        [InlineKeyboardButton("🎬 ᴍᴏᴠɪᴇꜱ", callback_data=f"{query_key}|movie|all|all|all"),
         InlineKeyboardButton("📺 ꜱᴇʀɪᴇꜱ", callback_data=f"{query_key}|series|all|all|all")],
        [InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ 🚫", callback_data="close_data")]
    ]

def build_season_buttons(query_key, req_type, files):
    seasons = get_seasons(files)
    btn_list = []
    for s in seasons:
        btn_list.append(InlineKeyboardButton(f"Sᴇᴀꜱᴏɴ {s}", callback_data=f"{query_key}|{req_type}|{s}|all|all"))
    btns = chunk_buttons(btn_list, 3)
    btns.insert(0, [InlineKeyboardButton("⇊ Sᴇʟᴇᴄᴛ Sᴇᴀꜱᴏɴ ⇊", callback_data="ident")])
    if seasons:
        btns.append([InlineKeyboardButton("Aʟʟ Sᴇᴀꜱᴏɴꜱ", callback_data=f"{query_key}|{req_type}|all|all|all")])
    btns.append([InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ 🚫", callback_data="close_data")])
    return btns

def build_language_buttons(query_key, req_type, season, files):
    cache_entry = CACHE.get(query_key)
    if not cache_entry:
        return []
    languages = cache_entry["langs"]
    btn_list = []
    for i, l in enumerate(languages):
        btn_list.append(InlineKeyboardButton(f"{l.title()}", callback_data=f"{query_key}|{req_type}|{season}|{i}|all"))
    btns = chunk_buttons(btn_list, 3)
    btns.insert(0, [InlineKeyboardButton("⇊ Sᴇʟᴇᴄᴛ Lᴀɴɢᴜᴀɢᴇ ⇊", callback_data="ident")])
    if languages:
        btns.append([InlineKeyboardButton("Aʟʟ Lᴀɴɢᴜᴀɢᴇꜱ", callback_data=f"{query_key}|{req_type}|{season}|all|all")])
    if req_type == "series":
        btns.append([InlineKeyboardButton("🔙 Bᴀᴄᴋ ᴛᴏ Sᴇᴀꜱᴏɴꜱ", callback_data=f"{query_key}|{req_type}|all|all|all")])
    else:
        btns.append([InlineKeyboardButton("🔙 Bᴀᴄᴋ ᴛᴏ Tʏᴘᴇ", callback_data=f"{query_key}|all|all|all|all")])
    btns.append([InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ 🚫", callback_data="close_data")])
    return btns

def build_quality_buttons(query_key, req_type, season, language, files):
    cache_entry = CACHE.get(query_key)
    if not cache_entry:
        return []
    qualities = cache_entry["quals"]
    btn_list = []
    for i, q in enumerate(qualities):
        btn_list.append(InlineKeyboardButton(f"{q.title()}", callback_data=f"{query_key}|{req_type}|{season}|{language}|{i}"))
    btns = chunk_buttons(btn_list, 3)
    btns.insert(0, [InlineKeyboardButton("⇊ Sᴇʟᴇᴄᴛ Qᴜᴀʟɪᴛʏ ⇊", callback_data="ident")])
    if qualities:
        btns.append([InlineKeyboardButton("Aʟʟ Qᴜᴀʟɪᴛɪᴇꜱ", callback_data=f"{query_key}|{req_type}|{season}|{language}|all")])
    btns.append([InlineKeyboardButton("🔙 Bᴀᴄᴋ ᴛᴏ Lᴀɴɢᴜᴀɢᴇꜱ", callback_data=f"{query_key}|{req_type}|{season}|all|all")])
    btns.append([InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ 🚫", callback_data="close_data")])
    return btns

def build_files_buttons(query_key, req_type, season, lang, qual, files, page=0):
    cache_entry = CACHE.get(query_key)
    if not cache_entry:
        return []
        
    resolved_lang = lang
    if lang != "all" and lang.isdigit():
        resolved_lang = cache_entry["langs"][int(lang)]
    
    resolved_qual = qual
    if qual != "all" and qual.isdigit():
        resolved_qual = cache_entry["quals"][int(qual)]

    filtered_files = []
    for f in files:
        f_season = str(getattr(f, "season", ""))
        if req_type == "series" and season != "all" and f_season != season:
            continue
        f_lang = str(getattr(f, "language", "")).lower()
        if resolved_lang != "all" and f_lang != resolved_lang:
            continue
        f_qual = str(getattr(f, "quality", "")).lower()
        if resolved_qual != "all" and f_qual != resolved_qual:
            continue
        filtered_files.append(f)

    if req_type == "series":
        filtered_files.sort(key=lambda x: (getattr(x, "season", 0) or 0, getattr(x, "episode", 0) or 0))
    
    # Pagination: 20 per page
    limit = 20
    start = page * limit
    end = start + limit
    page_files = filtered_files[start:end]
    
    btns = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)} ≽ " + clean_filename(file.file_name), url=f"https://t.me/{temp.U_NAME}?start=bot_0_{file.file_id}")] for file in page_files]
    
    # Navigation row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⋞ ᴘʀᴇᴠ", callback_data=f"page|{query_key}|{req_type}|{season}|{lang}|{qual}|{page-1}"))
    if end < len(filtered_files):
        nav.append(InlineKeyboardButton("ɴᴇxᴛ ⋟", callback_data=f"page|{query_key}|{req_type}|{season}|{lang}|{qual}|{page+1}"))
    if nav:
        btns.append(nav)

    if not filtered_files:
        btns = [[InlineKeyboardButton("🚫 Nᴏ ꜰɪʟᴇꜱ ꜰᴏᴜɴᴅ ꜰᴏʀ ꜱᴇʟᴇᴄᴛᴇᴅ ꜰɪʟᴛᴇʀꜱ", callback_data="ident")]]
    else:
        # Create a deep link using temp.GETALL for the FIRST 100 matches only to save memory
        import uuid
        state_key = f"allfiles_{uuid.uuid4().hex[:10]}"
        temp.GETALL[state_key] = filtered_files[:100]
        btns.insert(0, [InlineKeyboardButton("📤 Sᴇɴᴅ Aʟʟ (100) 📤", url=f"https://t.me/{temp.U_NAME}?start={state_key}")])
        
    btns.append([InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data=f"{query_key}|{req_type}|{season}|{lang}|all")])
    btns.append([InlineKeyboardButton("🏠 Bᴀᴄᴋ ᴛᴏ Sᴛᴀʀᴛ", callback_data=f"{query_key}|all|all|all|all")])
    btns.append([InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ 🚫", callback_data="close_data")])
    return btns

def get_next_markup(query_key, req_type, season, lang, qual, files):
    # Check for multiple titles first to avoid "A Knight" vs "Family Guy" confusion
    unique_titles = get_titles(files)
    if len(unique_titles) > 1:
        return build_title_buttons(query_key, files)

    if req_type == "all":
        types = set(str(getattr(f, "type", "movie")).lower() for f in files)
        if len(types) > 1:
            return build_type_buttons(query_key)
        else:
            req_type = list(types)[0] if types else "movie"
            
    type_files = [f for f in files if str(getattr(f, "type", "movie")).lower() == req_type]
    
    if req_type == "series":
        if season == "all":
            return build_season_buttons(query_key, req_type, type_files)
                
    if lang == "all":
        return build_language_buttons(query_key, req_type, season, type_files)
            
    if qual == "all":
        return build_quality_buttons(query_key, req_type, season, lang, type_files)
            
    return build_files_buttons(query_key, req_type, season, lang, qual, files, page=0)



@Client.on_callback_query(filters.regex(r"^select_title\|"))
async def select_title_callback(client: Client, query: CallbackQuery):
    try:
        await query.answer()
        parts = query.data.split("|")
        if len(parts) < 3:
            return
        _, query_key, title_index = parts
        cache_entry = CACHE.get(query_key)
        if not cache_entry:
            return await query.answer("Cᴀᴄʜᴇ Exᴘɪʀᴇᴅ!", show_alert=True)
        
        try:
            title_index = int(title_index)
            title_name = cache_entry["titles"][title_index]
        except:
            return await query.answer("Iɴᴠᴀʟɪᴅ Sᴇʟᴇᴄᴛɪᴏɴ!", show_alert=True)
        
        # Filter cache to ONLY this title
        cache_entry["files"] = [f for f in cache_entry["files"] if getattr(f, "title", "").lower() == title_name.lower()]
        
        # Re-generate metadata lists for THIS specific title
        cache_entry["langs"] = get_languages(cache_entry["files"])
        cache_entry["quals"] = get_qualities(cache_entry["files"])
        
        # Now continue to next markup
        markup = get_next_markup(query_key, "all", "all", "all", "all", cache_entry["files"])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(markup))
    except Exception as e:
        logger.exception(f"select_title_callback error: {e}")




@Client.on_message(filters.group & filters.text & filters.incoming & ~filters.regex(r"^/") )
async def give_filter(client, message):
    if EMOJI_MODE:
        try:
            await message.react(emoji=random.choice(REACTIONS), big=True)
        except Exception:
            await message.react(emoji="⚡️")
            pass
    await mdb.update_top_messages(message.from_user.id, message.text)
    if message.chat.id != SUPPORT_CHAT_ID:
        settings = await get_settings(message.chat.id)
        try:
            if settings['auto_ffilter']:
                if re.search(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
                    if await is_check_admin(client, message.chat.id, message.from_user.id):
                        return
                    return await message.delete()
                await auto_filter(client, message)
        except KeyError:
            pass
    else:
        search = message.text
        _, _, total_results = await get_search_results(chat_id=message.chat.id, query=search.lower(), offset=0, filter=True)
        if total_results == 0:
            return
        await message.reply_text(
            f"<b>Hᴇʏ {message.from_user.mention},\n\n"
            f"ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ✅\n\n"
            f"📂 ꜰɪʟᴇꜱ ꜰᴏᴜɴᴅ : {str(total_results)}\n"
            f"🔍 ꜱᴇᴀʀᴄʜ :</b> <code>{search}</code>\n\n"
            f"<b>‼️ ᴛʜɪs ɪs ᴀ <u>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</u> sᴏ ᴛʜᴀᴛ ʏᴏᴜ ᴄᴀɴ'ᴛ ɢᴇᴛ ғɪʟᴇs ғʀᴏᴍ ʜᴇʀᴇ...\n\n"
            f"📝 ꜱᴇᴀʀᴄʜ ʜᴇʀᴇ : 👇</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔍 ᴊᴏɪɴ ᴀɴᴅ ꜱᴇᴀʀᴄʜ ʜᴇʀᴇ 🔎", url=GRP_LNK)]])
        )


@Client.on_message(filters.private & filters.text & filters.incoming & ~filters.regex(r"^/") & ~filters.regex(r"(https?://)?(t\.me|telegram\.me|telegram\.dog)/"))
async def pm_text(bot, message):
    bot_id = bot.me.id
    content = message.text
    user = message.from_user.first_name
    user_id = message.from_user.id
    if EMOJI_MODE:
        try:
            await message.react(emoji=random.choice(REACTIONS), big=True)
        except Exception:
            await message.react(emoji="⚡️")
            pass
    if content.startswith(("#")):
        return
    try:
        await mdb.update_top_messages(user_id, content)
        pm_search = await db.pm_search_status(bot_id)
        if pm_search:
            await auto_filter(bot, message)
        else:
            await message.reply_text(
                text=(
                    f"<b>🙋 ʜᴇʏ {user} 😍 ,\n\n"
                    "𝒀𝒐𝒖 𝒄𝒂𝒏 𝒔𝒆𝒂𝒓𝒄𝒉 𝒇𝒐𝒓 𝒎𝒐𝒗𝒊𝒆𝒔 𝒐𝒏𝒍𝒚 𝒐𝒏 𝒐𝒖𝒓 𝑴𝒐𝒗𝒊𝒆 𝑮𝒓𝒐𝒖𝒑. 𝒀𝒐𝒖 𝒂𝒓𝒆 𝒏𝒐𝒕 𝒂𝒍𝒍𝒐𝒘𝒆𝒅 𝒕𝒐 𝒔𝒆𝒂𝒓𝒄𝒉 𝒇𝒐𝒓 𝒎𝒐𝒗𝒊𝒆𝒔 𝒐𝒏 𝑫𝒊𝒓𝒆𝒄𝒕 𝑩𝒐𝒕. 𝑷𝒍𝒆𝒂𝒔𝒆 𝒋𝒐𝒊𝒏 𝒐𝒖𝒓 𝒎𝒐𝒗𝒊𝒆 𝒈𝒓𝒐𝒖𝒑 𝒃𝒚 𝒄𝒍𝒊𝒄𝒌𝒊𝒏𝒈 𝒐𝒏 𝒕𝒉𝒆  𝑹𝑬𝑸𝑼𝑬𝑺𝑻 𝑯𝑬𝑹𝑬 𝒃𝒖𝒕𝒕𝒐𝒏 𝒈𝒊𝒗𝒆𝒏 𝒃𝒆𝒍𝒐𝒘 𝒂𝒏𝒅 𝒔𝒆𝒂𝒓𝒄𝒉 𝒚𝒐𝒖𝒓 𝒇𝒂𝒗𝒐𝒓𝒊𝒕𝒆 𝒎𝒐𝒗𝒊𝒆 𝒕𝒉𝒆𝒓𝒆 👇\n\n"
                    "<blockquote>"
                    "आप केवल हमारे 𝑴𝒐𝒗𝒊𝒆 𝑮𝒓𝒐𝒖𝒑 पर ही 𝑴𝒐𝒗𝒊𝒆 𝑺𝒆𝒂𝒓𝒄𝒉 कर सकते हो । "
                    "आपको 𝑫𝒊𝒓𝒆𝒄𝒕 𝑩𝒐𝒕 पर 𝑴𝒐𝒗𝒊𝒆 𝑺𝒆𝒂𝒓𝒄𝒉 करने की 𝑷𝒆𝒓𝒎𝒊𝒔𝒔𝒊𝒐𝒏 नहीं है कृपया नीचे दिए गए 𝑹𝑬𝑸𝑼𝑬𝑺𝑻 𝑯𝑬𝑹𝑬 वाले 𝑩𝒖𝒕𝒕𝒐𝒏 पर क्लिक करके हमारे 𝑴𝒐𝒗𝒊𝒆 𝑮𝒓𝒐𝒖𝒑 को 𝑱𝒐𝒊𝒏 करें और वहां पर अपनी मनपसंद 𝑴𝒐𝒗𝒊𝒆 𝑺𝒆𝒂𝒓𝒄𝒉 सर्च करें ।"
                    "</blockquote></b>"
                ), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 ʀᴇǫᴜᴇsᴛ ʜᴇʀᴇ ", url=GRP_LNK)]]))
            await bot.send_message(chat_id=LOG_CHANNEL,
                                   text=(
                                       f"<b>#𝐏𝐌_𝐌𝐒𝐆\n\n"
                                       f"👤 Nᴀᴍᴇ : {user}\n"
                                       f"🆔 ID : {user_id}\n"
                                       f"💬 Mᴇssᴀɢᴇ : {content}</b>"
                                   )
                                   )
    except Exception:
        pass





@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    movies = await get_posterx(id, id=True) if TMDB_ON_SEARCH else await get_poster(id, id=True)
    movie = movies.get('title')
    movie = re.sub(r"[:-]", " ", movie)
    movie = re.sub(r"\s+", " ", movie).strip()
    await query.answer(script.TOP_ALRT_MSG)
    files, offset, total_results = await get_search_results(query.message.chat.id, movie, offset=0, filter=True, max_results=1000)
    if files:
        k = (movie, files, offset, total_results)
        await auto_filter(bot, query, k)
    else:
        reqstr1 = query.from_user.id if query.from_user else 0
        reqstr = await bot.get_users(reqstr1)
        if NO_RESULTS_MSG:
            try:
                await bot.send_message(chat_id=BIN_CHANNEL, text=script.NORSLTS.format(reqstr.id, reqstr.mention, movie))
            except Exception as e:
                logger.error(f"Error In Spell Check - {e}. Make sure the bot is an admin in the BIN_CHANNEL.")
        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔰Cʟɪᴄᴋ ʜᴇʀᴇ & ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴀᴅᴍɪɴ🔰", url=OWNER_LNK)]])
        k = await query.message.edit(script.MVE_NT_FND, reply_markup=btn)
        await asyncio.sleep(10)
        await k.delete()

@Client.on_callback_query(filters.regex(r"^page\|"))
async def pagination_callback(client: Client, query: CallbackQuery):
    try:
        await query.answer()
        parts = query.data.split("|")
        if len(parts) != 7:
            return
            
        _, query_key, req_type, season, lang_idx, qual_idx, page = parts
        cache_entry = CACHE.get(query_key)
        if not cache_entry:
            return await query.edit_message_reply_markup(reply_markup=None)

        try:
            page = int(page)
        except:
            page = 0

        files = cache_entry["files"]
        markup = build_files_buttons(query_key, req_type, season, lang_idx, qual_idx, files, page=page)
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(markup))
    except Exception as e:
        logger.exception(f"pagination_callback error: {e}")

@Client.on_callback_query(filters.regex(r"^([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)$"))
async def new_hierarchical_filter_callback(client: Client, query: CallbackQuery):
    try:
        await query.answer()
        data = query.data
        parts = data.split("|", 4)
        if len(parts) != 5:
            return
            
        query_key, req_type, season, lang_idx, qual_idx = parts
        
        try:
            if int(query.from_user.id) not in [query.message.reply_to_message.from_user.id, 0]:
                return await query.answer("⚠️ Tʜɪꜱ ɪꜱ ɴᴏᴛ ʏᴏᴜʀ ᴍᴏᴠɪᴇ ʀᴇǫᴜᴇꜱᴛ!", show_alert=True)
        except:
            pass

        cache_entry = CACHE.get(query_key)
        if not cache_entry:
            return await query.answer("Cᴀᴄʜᴇ Exᴘɪʀᴇᴅ! Pʟᴇᴀꜱᴇ ꜱᴇᴀʀᴄʜ ᴀɢᴀɪɴ.", show_alert=True)
            
        files = cache_entry["files"]
        markup = get_next_markup(query_key, req_type, season, lang_idx, qual_idx, files)
        
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(markup))
    except MessageNotModified:
        pass
    except Exception as e:
        logger.exception(f"hierarchical_filter error: {e}")


@Client.on_callback_query(group=10)
async def cb_handler(client: Client, query: CallbackQuery):
    MoviebotData = query.data
    try:
        link = await client.create_chat_invite_link(int(REQST_CHANNEL))
    except:
        pass
    if query.data == "close_data":
        try:
            user = query.message.reply_to_message.from_user.id
        except:
            user = query.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(script.NT_ALRT_TXT, show_alert=True)
        await query.answer("ᴛʜᴀɴᴋs ꜰᴏʀ ᴄʟᴏsᴇ 🙈")
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
            
    elif query.data == "ident":
        await query.answer()

    elif query.data == "pages":
        await query.answer("ᴛʜɪs ɪs ᴘᴀɢᴇs ʙᴜᴛᴛᴏɴ 😅")

    elif query.data == "hiding":
        await query.answer("ʙᴇᴄᴀᴜsᴇ ᴏғ ʟᴀɢᴛᴇ ғɪʟᴇs ɪɴ ᴅᴀᴛᴀʙᴀsᴇ,🙏\nɪᴛ ᴛᴀᴋᴇꜱ ʟɪᴛᴛʟᴇ ʙɪᴛ ᴛɪᴍᴇ",show_alert=True)

    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = enums.ChatType(query.message.chat.type)
        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("Tʜᴀᴛ's ɴᴏᴛ ғᴏʀ ʏᴏᴜ!!", show_alert=True)



    elif query.data.startswith("del"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"
        await query.answer(url=f"href='https://telegram.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}")

    elif query.data.startswith("autofilter_delete"):
        await Media.collection.drop()
        if MULTIPLE_DB:    
            await Media2.collection.drop()
        await query.answer("Eᴠᴇʀʏᴛʜɪɴɢ's Gᴏɴᴇ")
        await query.message.edit('ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴀʟʟ ɪɴᴅᴇxᴇᴅ ꜰɪʟᴇꜱ ✅')

    elif query.data.startswith("checksub"):
        try:
            ident, kk, file_id = query.data.split("#")
            btn = []
            chat = file_id.split("_")[0]
            settings = await get_settings(chat)
            fsub_channels = list(dict.fromkeys((settings.get('fsub', []) if settings else [])+ AUTH_CHANNELS)) 
            btn += await is_subscribed(client, query.from_user.id, fsub_channels, chat_id=grp_id)
            btn += await is_req_subscribed(client, query.from_user.id, AUTH_REQ_CHANNELS)
            if btn:
                btn.append([InlineKeyboardButton("♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️", callback_data=f"checksub#{kk}#{file_id}")])
                try:
                    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
                except MessageNotModified:
                    pass
                await query.answer(
                    f"👋 Hello {query.from_user.first_name},\n\n"
                    "🛑 Yᴏᴜ ʜᴀᴠᴇ ɴᴏᴛ ᴊᴏɪɴᴇᴅ ᴀʟʟ ʀᴇǫᴜɪʀᴇᴅ ᴜᴘᴅᴀᴛᴇ Cʜᴀɴɴᴇʟs.\n"
                    "👉 Pʟᴇᴀsᴇ ᴊᴏɪɴ ᴇᴀᴄʜ ᴏɴᴇ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.\n",
                    show_alert=True
                )
                return
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={kk}_{file_id}")
            await query.message.delete()
        except Exception as e:
            await log_error(client, f"❌ Error in checksub callback:\n\n{repr(e)}")
            logger.error(f"❌ Error in checksub callback:\n\n{repr(e)}")


    elif query.data.startswith("killfilesdq"):
        ident, keyword = query.data.split("#")
        await query.message.edit_text(f"<b>Fetching Files for your query {keyword} on DB... Please wait...</b>")
        files, total = await get_bad_files(keyword)
        await query.message.edit_text("<b>ꜰɪʟᴇ ᴅᴇʟᴇᴛɪᴏɴ ᴘʀᴏᴄᴇꜱꜱ ᴡɪʟʟ ꜱᴛᴀʀᴛ ɪɴ 5 ꜱᴇᴄᴏɴᴅꜱ !</b>")
        await asyncio.sleep(5)
        deleted = 0
        async with lock:
            try:
                for file in files:
                    file_ids = file.file_id
                    file_name = file.file_name
                    result = await Media.collection.delete_one({
                        '_id': file_ids,
                    })
                    if not result.deleted_count and MULTIPLE_DB:
                        result = await Media2.collection.delete_one({
                            '_id': file_ids,
                        })
                    if result.deleted_count:
                        logger.info(
                            f'ꜰɪʟᴇ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ ǫᴜᴇʀʏ {keyword}! ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {file_name} ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀꜱᴇ.')
                    deleted += 1
                    if deleted % 20 == 0:
                        await query.message.edit_text(f"<b>ᴘʀᴏᴄᴇꜱꜱ ꜱᴛᴀʀᴛᴇᴅ ꜰᴏʀ ᴅᴇʟᴇᴛɪɴɢ ꜰɪʟᴇꜱ ꜰʀᴏᴍ ᴅʙ. ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {str(deleted)} ꜰɪʟᴇꜱ ꜰʀᴏᴍ ᴅʙ ꜰᴏʀ ʏᴏᴜʀ ǫᴜᴇʀʏ {keyword} !\n\nᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ...</b>")
            except Exception as e:
                print(f"Error In killfiledq -{e}")
                await query.message.edit_text(f'Error: {e}')
            else:
                await query.message.edit_text(f"<b>ᴘʀᴏᴄᴇꜱꜱ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ꜰᴏʀ ꜰɪʟᴇ ᴅᴇʟᴇᴛᴀᴛɪᴏɴ !\n\nꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {str(deleted)} ꜰɪʟᴇꜱ ꜰʀᴏᴍ ᴅʙ ꜰᴏʀ ʏᴏᴜʀ ǫᴜᴇʀʏ {keyword}.</b>")

    elif query.data.startswith("opnsetgrp"):
        ident, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
            await query.answer("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ʀɪɢʜᴛꜱ ᴛᴏ ᴅᴏ ᴛʜɪꜱ !", show_alert=True)
            return
        title = query.message.chat.title
        settings = await get_settings(grp_id)
        if settings is not None:
            btn = await group_setting_buttons(int(grp_id))
            reply_markup = InlineKeyboardMarkup(btn)
            await query.message.edit_text(
                text=f"<b>ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ꜱᴇᴛᴛɪɴɢꜱ ꜰᴏʀ {title} ᴀꜱ ʏᴏᴜ ᴡɪꜱʜ ⚙</b>",
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML
            )
            await query.message.edit_reply_markup(reply_markup)

    elif query.data.startswith("opnsetpm"):
        ident, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if (
                st.status != enums.ChatMemberStatus.ADMINISTRATOR
                and st.status != enums.ChatMemberStatus.OWNER
                and str(userid) not in ADMINS
        ):
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
            return
        title = query.message.chat.title
        settings = await get_settings(grp_id)
        btn2 = [[
            InlineKeyboardButton(
                "ᴄʜᴇᴄᴋ ᴍʏ ᴅᴍ 🗳️", url=f"telegram.me/{temp.U_NAME}")
        ]]
        reply_markup = InlineKeyboardMarkup(btn2)
        await query.message.edit_text(f"<b>ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ ғᴏʀ {title} ʜᴀs ʙᴇᴇɴ sᴇɴᴛ ᴛᴏ ʏᴏᴜ ʙʏ ᴅᴍ.</b>")
        await query.message.edit_reply_markup(reply_markup)
        if settings is not None:
            btn = await group_setting_buttons(int(grp_id))
            reply_markup = InlineKeyboardMarkup(btn)
            await client.send_message(
                chat_id=userid,
                text=f"<b>ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ꜱᴇᴛᴛɪɴɢꜱ ꜰᴏʀ {title} ᴀꜱ ʏᴏᴜ ᴡɪꜱʜ ⚙</b>",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=query.message.id
            )

    elif query.data.startswith("show_option"):
        ident, from_user = query.data.split("#")
        btn = [[
            InlineKeyboardButton("⚠️ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️",
                                 callback_data=f"unavailable#{from_user}"),
            InlineKeyboardButton(
                "🟢 ᴜᴘʟᴏᴀᴅᴇᴅ 🟢", callback_data=f"uploaded#{from_user}")
        ], [
            InlineKeyboardButton("♻️ ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ♻️",
                                 callback_data=f"already_available#{from_user}")
        ], [
            InlineKeyboardButton("📌 Not Released 📌",
                                 callback_data=f"Not_Released#{from_user}"),
            InlineKeyboardButton("♨️Type Correct Spelling♨️",
                                 callback_data=f"Type_Correct_Spelling#{from_user}")
        ], [
            InlineKeyboardButton("⚜️ Not Available In The Hindi ⚜️",
                                 callback_data=f"Not_Available_In_The_Hindi#{from_user}")
        ]]
        btn2 = [[
            InlineKeyboardButton("ᴠɪᴇᴡ ꜱᴛᴀᴛᴜꜱ", url=f"{query.message.link}")
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Hᴇʀᴇ ᴀʀᴇ ᴛʜᴇ ᴏᴘᴛɪᴏɴs !")
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("unavailable"):
        ident, from_user = query.data.split("#")
        btn = [[InlineKeyboardButton(
            "⚠️ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️",
            callback_data=f"unalert#{from_user}")]]
        btn2 = [[
            InlineKeyboardButton('ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ', url=link.invite_link),
            InlineKeyboardButton("ᴠɪᴇᴡ ꜱᴛᴀᴛᴜꜱ", url=f"{query.message.link}")
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Uɴᴀᴠᴀɪʟᴀʙʟᴇ !")
            content = extract_request_content(query.message.text)
            try:
                await client.send_message(
                    chat_id=int(from_user),
                    text=f"<b>Hᴇʏ {user.mention},</b>\n\n<u>{content}</u> Hᴀs Bᴇᴇɴ Mᴀʀᴋᴇᴅ Aᴅ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ...💔\n\n#Uɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️",
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
            except UserIsBlocked:
                await client.send_message(
                    chat_id=int(SUPPORT_CHAT_ID),
                    text=f"<b>Hᴇʏ {user.mention},</b>\n\n<u>{content}</u> Hᴀs Bᴇᴇɴ Mᴀʀᴋᴇᴅ Aᴅ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ...💔\n\n#Uɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️\n\n<small>Bʟᴏᴄᴋᴇᴅ? Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ʀᴇᴄᴇɪᴠᴇ ᴍᴇꜱꜱᴀɢᴇꜱ.</small></b>",
                    reply_markup=InlineKeyboardMarkup(btn2)
                )

    elif query.data.startswith("Not_Released"):
        ident, from_user = query.data.split("#")
        btn = [[InlineKeyboardButton(
            "📌 Not Released 📌", callback_data=f"nralert#{from_user}")]]
        btn2 = [[
            InlineKeyboardButton('ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ', url=link.invite_link),
            InlineKeyboardButton("ᴠɪᴇᴡ ꜱᴛᴀᴛᴜꜱ", url=f"{query.message.link}")
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Nᴏᴛ Rᴇʟᴇᴀꜱᴇᴅ !")
            content = extract_request_content(query.message.text)
            try:
                await client.send_message(
                    chat_id=int(from_user),
                    text=(
                        f"<b>Hᴇʏ {user.mention}\n\n"
                        f"<code>{content}</code>, ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ʜᴀꜱ ɴᴏᴛ ʙᴇᴇɴ ʀᴇʟᴇᴀꜱᴇᴅ ʏᴇᴛ\n\n"
                        f"#CᴏᴍɪɴɢSᴏᴏɴ...🕊️✌️</b>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
            except UserIsBlocked:
                await client.send_message(
                    chat_id=int(SUPPORT_CHAT_ID),
                    text=(
                        f"<u>Hᴇʏ {user.mention}</u>\n\n"
                        f"<b><code>{content}</code>, ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ʜᴀꜱ ɴᴏᴛ ʙᴇᴇɴ ʀᴇʟᴇᴀꜱᴇᴅ ʏᴇᴛ\n\n"
                        f"#CᴏᴍɪɴɢSᴏᴏɴ...🕊️✌️\n\n"
                        f"<small>Bʟᴏᴄᴋᴇᴅ? Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ʀᴇᴄᴇɪᴠᴇ ᴍᴇꜱꜱᴀɢᴇꜱ.</small></b>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("Type_Correct_Spelling"):
        ident, from_user = query.data.split("#")
        btn = [[
            InlineKeyboardButton("♨️ Type Correct Spelling ♨️",
                                 callback_data=f"wsalert#{from_user}")
        ]]
        btn2 = [[
            InlineKeyboardButton('ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ', url=link.invite_link),
            InlineKeyboardButton("ᴠɪᴇᴡ ꜱᴛᴀᴛᴜꜱ", url=f"{query.message.link}")
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Cᴏʀʀᴇᴄᴛ Sᴘᴇʟʟɪɴɢ !")
            content = extract_request_content(query.message.text)
            try:
                await client.send_message(
                    chat_id=int(from_user),
                    text=(
                        f"<b>Hᴇʏ {user.mention}\n\n"
                        f"Wᴇ Dᴇᴄʟɪɴᴇᴅ Yᴏᴜʀ Rᴇǫᴜᴇsᴛ <code>{content}</code>, Bᴇᴄᴀᴜsᴇ Yᴏᴜʀ Sᴘᴇʟʟɪɴɢ Wᴀs Wʀᴏɴɢ 😢\n\n"
                        f"#Wʀᴏɴɢ_Sᴘᴇʟʟɪɴɢ 😑</b>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
            except UserIsBlocked:
                await client.send_message(
                    chat_id=int(SUPPORT_CHAT_ID),
                    text=(
                        f"<u>Hᴇʏ {user.mention}</u>\n\n"
                        f"<b><code>{content}</code>, Bᴇᴄᴀᴜsᴇ Yᴏᴜʀ Sᴘᴇʟʟɪɴɢ Wᴀs Wʀᴏɴɢ 😢\n\n"
                        f"#Wʀᴏɴɢ_Sᴘᴇʟʟɪɴɢ 😑\n\n"
                        f"<small>Bʟᴏᴄᴋᴇᴅ? Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ʀᴇᴄᴇɪᴠᴇ ᴍᴇꜱꜱᴀɢᴇꜱ.</small></b>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("Not_Available_In_The_Hindi"):
        ident, from_user = query.data.split("#")
        btn = [[
            InlineKeyboardButton(
                "⚜️ Not Available In The Hindi ⚜️", callback_data=f"hnalert#{from_user}")
        ]]
        btn2 = [[
            InlineKeyboardButton('ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ', url=link.invite_link),
            InlineKeyboardButton("ᴠɪᴇᴡ ꜱᴛᴀᴛᴜꜱ", url=f"{query.message.link}")
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Nᴏᴛ Aᴠᴀɪʟᴀʙʟᴇ Iɴ Hɪɴᴅɪ !")
            content = extract_request_content(query.message.text)
            try:
                await client.send_message(
                    chat_id=int(from_user),
                    text=(
                        f"<b>Hᴇʏ {user.mention}\n\n"
                        f"Yᴏᴜʀ Rᴇǫᴜᴇsᴛ <code>{content}</code> ɪs Nᴏᴛ Aᴠᴀɪʟᴀʙʟᴇ ɪɴ Hɪɴᴅɪ ʀɪɢʜᴛ ɴᴏᴡ. Sᴏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ɪᴛ\n\n"
                        f"#Hɪɴᴅɪ_ɴᴏᴛ_ᴀᴠᴀɪʟᴀʙʟᴇ ❌</b>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
            except UserIsBlocked:
                await client.send_message(
                    chat_id=int(SUPPORT_CHAT_ID),
                    text=(
                        f"<u>Hᴇʏ {user.mention}</u>\n\n"
                        f"<b><code>{content}</code> ɪs Nᴏᴛ Aᴠᴀɪʟᴀʙʟᴇ ɪɴ Hɪɴᴅɪ ʀɪɢʜᴛ ɴᴏᴡ. Sᴏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ɪᴛ\n\n"
                        f"#Hɪɴᴅɪ_ɴᴏᴛ_ᴀᴠᴀɪʟᴀʙʟᴇ ❌\n\n"
                        f"<small>Bʟᴏᴄᴋᴇᴅ? Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ʀᴇᴄᴇɪᴠᴇ ᴍᴇꜱꜱᴀɢᴇꜱ.</small></b>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("uploaded"):
        ident, from_user = query.data.split("#")
        btn = [[
            InlineKeyboardButton(
                "🟢 ᴜᴘʟᴏᴀᴅᴇᴅ 🟢", callback_data=f"upalert#{from_user}")
        ]]
        btn2 = [[
            InlineKeyboardButton('ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ', url=link.invite_link),
            InlineKeyboardButton("ᴠɪᴇᴡ ꜱᴛᴀᴛᴜꜱ", url=f"{query.message.link}")
        ], [
            InlineKeyboardButton("🔍 ꜱᴇᴀʀᴄʜ ʜᴇʀᴇ 🔎", url=GRP_LNK)
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Uᴘʟᴏᴀᴅᴇᴅ !")
            content = extract_request_content(query.message.text)
            try:
                await client.send_message(
                    chat_id=int(from_user),
                    text=(
                        f"<b>Hᴇʏ {user.mention},\n\n"
                        f"<u>{content}</u> Yᴏᴜr ʀᴇǫᴜᴇꜱᴛ ʜᴀꜱ ʙᴇᴇɴ ᴜᴘʟᴏᴀᴅᴇᴅ ʙʏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs.\n"
                        f"Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>\n\n"
                        f"#Uᴘʟᴏᴀᴅᴇᴅ✅"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
            except UserIsBlocked:
                await client.send_message(
                    chat_id=int(SUPPORT_CHAT_ID),
                    text=(
                        f"<u>{content}</u>\n\n"
                        f"<b>Hᴇʏ {user.mention}, Yᴏᴜr ʀᴇǫᴜᴇꜱᴛ ʜᴀꜱ ʙᴇᴇɴ ᴜᴘʟᴏᴀᴅᴇᴅ ʙʏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs."
                        f"Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>\n\n"
                        f"#Uᴘʟᴏᴀᴅᴇᴅ✅\n\n"
                        f"<small>Bʟᴏᴄᴋᴇᴅ? Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ʀᴇᴄᴇɪᴠᴇ ᴍᴇꜱꜱᴀɢᴇꜱ.</small>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("already_available"):
        ident, from_user = query.data.split("#")
        btn = [[
            InlineKeyboardButton("♻️ ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ♻️",
                                 callback_data=f"alalert#{from_user}")
        ]]
        btn2 = [[
            InlineKeyboardButton('ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ', url=link.invite_link),
            InlineKeyboardButton("ᴠɪᴇᴡ ꜱᴛᴀᴛᴜꜱ", url=f"{query.message.link}")
        ], [
            InlineKeyboardButton("🔍 ꜱᴇᴀʀᴄʜ ʜᴇʀᴇ 🔎", url=GRP_LNK)
        ]]
        if query.from_user.id in ADMINS:
            user = await client.get_users(from_user)
            reply_markup = InlineKeyboardMarkup(btn)
            content = query.message.text
            await query.message.edit_text(f"<b><strike>{content}</strike></b>")
            await query.message.edit_reply_markup(reply_markup)
            await query.answer("Sᴇᴛ ᴛᴏ Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ !")
            content = extract_request_content(query.message.text)
            try:
                await client.send_message(
                    chat_id=int(from_user),
                    text=(
                        f"<b>Hᴇʏ {user.mention},\n\n"
                        f"<u>{content}</u> Yᴏᴜr ʀᴇǫᴜᴇꜱᴛ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ ᴏᴜʀ ʙᴏᴛ'ꜱ ᴅᴀᴛᴀʙᴀꜱᴇ.\n"
                        f"Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>\n\n"
                        f"#Aᴠᴀɪʟᴀʙʟᴇ 💗"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
            except UserIsBlocked:
                await client.send_message(
                    chat_id=int(SUPPORT_CHAT_ID),
                    text=(
                        f"<b>Hᴇʏ {user.mention},\n\n"
                        f"<u>{content}</u> Yᴏᴜr ʀᴇǫᴜᴇꜱᴛ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ ᴏᴜʀ ʙᴏᴛ'ꜱ ᴅᴀᴛᴀʙᴀꜱᴇ.\n"
                        f"Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>\n\n"
                        f"#Aᴠᴀɪʟᴀʙʟᴇ 💗\n"
                        f"<small>Bʟᴏᴄᴋᴇᴅ? Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ʀᴇᴄᴇɪᴠᴇ ᴍᴇꜱꜱᴀɢᴇꜱ.</small></i>"
                    ),
                    reply_markup=InlineKeyboardMarkup(btn2)
                )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

    elif query.data.startswith("alalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(
                f"Hᴇʏ {user.first_name}, Yᴏᴜr ʀᴇǫᴜᴇꜱᴛ ɪꜱ Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ ✅",
                show_alert=True
            )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴇɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs ❌", show_alert=True)

    elif query.data.startswith("upalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(
                f"Hᴇʏ {user.first_name}, Yᴏᴜr ʀᴇǫᴜᴇꜱᴛ ɪꜱ Uᴘʟᴏᴀᴅᴇᴅ 🔼",
                show_alert=True
            )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴇɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs ❌", show_alert=True)

    elif query.data.startswith("unalert"):
        ident, from_user = query.data.split("#")
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(
                f"Hᴇʏ {user.first_name}, Yᴏᴜr ʀᴇǫᴜᴇꜱᴛ ɪꜱ Uɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️",
                show_alert=True
            )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴇɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs ❌", show_alert=True)

    elif query.data.startswith("hnalert"):
        ident, from_user = query.data.split("#")  # Hindi Not Available
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(
                f"Hᴇʏ {user.first_name}, Tʜɪꜱ ɪꜱ Nᴏᴛ Aᴠᴀɪʟᴀʙʟᴇ ɪɴ Hɪɴᴅɪ ❌",
                show_alert=True
            )
        else:
            await query.answer("Nᴏᴛ ᴀʟʟᴏᴡᴇᴅ — ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴛʜᴇ ʀᴇǫᴜᴇꜱᴛᴇʀ ❌", show_alert=True)

    elif query.data.startswith("nralert"):
        ident, from_user = query.data.split("#")  # Not Released
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(
                f"Hᴇʏ {user.first_name}, Tʜᴇ Mᴏᴠɪᴇ/ꜱʜᴏᴡ ɪꜱ Nᴏᴛ Rᴇʟᴇᴀꜱᴇᴅ Yᴇᴛ 🆕",
                show_alert=True
            )
        else:
            await query.answer("Yᴏᴜ ᴄᴀɴ'ᴛ ᴅᴏ ᴛʜɪꜱ ᴀꜱ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴛʜᴇ ᴏʀɪɢɪɴᴀʟ ʀᴇǫᴜᴇꜱᴛᴇʀ ❌", show_alert=True)

    elif query.data.startswith("wsalert"):
        ident, from_user = query.data.split("#")  # Wrong Spelling
        if int(query.from_user.id) == int(from_user):
            user = await client.get_users(from_user)
            await query.answer(
                f"Hᴇʏ {user.first_name}, Yᴏᴜr Rᴇǫᴜᴇꜱᴛ ᴡᴀꜱ ʀᴇᴊᴇᴄᴛᴇᴅ ᴅᴜᴇ ᴛᴏ ᴡʀᴏɴɢ sᴘᴇʟʟɪɴɢ ❗",
                show_alert=True
            )
        else:
            await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ sᴇᴇ ᴛʜɪꜱ ❌", show_alert=True)

    elif query.data == "pagesn1":
        await query.answer(text=script.PAGE_TXT, show_alert=True)

    elif query.data == "sinfo":
        await query.answer(text=script.SINFO, show_alert=True)

    elif query.data == "start":
        buttons = [[
                    InlineKeyboardButton('🔰 ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ 🔰', url=f'http://telegram.me/{temp.U_NAME}?startgroup=true')
                ],[
                    InlineKeyboardButton(' ʜᴇʟᴘ 📢', callback_data='help'),
                    InlineKeyboardButton(' ᴀʙᴏᴜᴛ 📖', callback_data='about')
                ],[
                    InlineKeyboardButton('ᴛᴏᴘ sᴇᴀʀᴄʜɪɴɢ ⭐', callback_data="topsearch"),
                ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        current_time = datetime.now(pytz.timezone(TIMEZONE))
        curr_time = current_time.hour
        if curr_time < 12:
            gtxt = "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞"
        elif curr_time < 17:
            gtxt = "ɢᴏᴏᴅ ᴀғᴛᴇʀɴᴏᴏɴ 🌓"
        elif curr_time < 21:
            gtxt = "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"
        else:
            gtxt = "ɢᴏᴏᴅ ɴɪɢʜᴛ 🌑"
        try:
            try:
                PIC = f"{random.choice(PICS_URL)}?r={get_random_mix_id()}"
            except Exception:
                PIC = random.choice(PICS)
            await client.edit_message_media(
                query.message.chat.id,
                query.message.id,
                InputMediaPhoto(PIC)
            )
        except Exception as e:
            pass
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, gtxt, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer(MSG_ALRT)

    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('⇋ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ⇋', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('‼️ ᴅɪꜱᴄʟᴀɪᴍᴇʀ ‼️', callback_data='disclaimer')
        ],[
            InlineKeyboardButton('⇋ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ⇋', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.U_NAME, temp.B_NAME, OWNER_LNK),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML
        )


    elif query.data == "disclaimer":
            btn = [[
                    InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data="about")
                  ]]
            reply_markup = InlineKeyboardMarkup(btn)
            await query.message.edit_text(
                text=(script.DISCLAIMER_TXT),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )

    elif query.data.startswith("grp_pm"):
        _, grp_id = query.data.split("#")
        user_id = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), user_id):
            return await query.answer(script.NT_ADMIN_ALRT_TXT, show_alert=True)

        btn = await group_setting_buttons(int(grp_id))
        moviebot_chat = await client.get_chat(int(grp_id))
        await query.message.edit(text=f"ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ ✅\nɢʀᴏᴜᴘ ɴᴀᴍᴇ - '{moviebot_chat.title}'</b>⚙", reply_markup=InlineKeyboardMarkup(btn))

    elif query.data.startswith("removegrp"):
        user_id = query.from_user.id
        data = query.data
        grp_id = int(data.split("#")[1])
        if not await is_check_admin(client, grp_id, query.from_user.id):
            return await query.answer(script.NT_ADMIN_ALRT_TXT, show_alert=True)
        await db.remove_group_connection(grp_id, user_id)
        await query.answer("Group removed from your connections.", show_alert=True)
        connected_groups = await db.get_connected_grps(user_id)
        if not connected_groups:
            await query.edit_message_text("Nᴏ Cᴏɴɴᴇᴄᴛᴇᴅ Gʀᴏᴜᴘs Fᴏᴜɴᴅ .")
            return
        group_list = []
        for group in connected_groups:
            try:
                Chat = await client.get_chat(group)
                group_list.append([
                    InlineKeyboardButton(
                        text=Chat.title, callback_data=f"grp_pm#{Chat.id}")
                ])
            except Exception as e:
                print(f"Error In PM Settings Button - {e}")
                pass
        await query.edit_message_text(
            "⚠️ ꜱᴇʟᴇᴄᴛ ᴛʜᴇ ɢʀᴏᴜᴘ ᴡʜᴏꜱᴇ ꜱᴇᴛᴛɪɴɢꜱ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ.\n\n"
            "ɪꜰ ʏᴏᴜʀ ɢʀᴏᴜᴘ ɪꜱ ɴᴏᴛ ꜱʜᴏᴡɪɴɢ ʜᴇʀᴇ,\n"
            "ᴜꜱᴇ /reload ɪɴ ᴛʜᴀᴛ ɢʀᴏᴜᴘ ᴀɴᴅ ɪᴛ ᴡɪʟʟ ᴀᴘᴘᴇᴀʀ ʜᴇʀᴇ.",
            reply_markup=InlineKeyboardMarkup(group_list)
        )

    try:
        if query.data.startswith("setgs"):
            await query.answer()
            ident, set_type, status, grp_id = query.data.split("#")
            userid = query.from_user.id if query.from_user else None
            if not await is_check_admin(client, int(grp_id), userid):
                await query.answer(script.NT_ADMIN_ALRT_TXT, show_alert=True)
                return
            
            if status == "True":
                await save_group_settings(int(grp_id), set_type, False)
                await query.answer("ᴏꜰꜰ ✗")
            elif status == "False":
                await save_group_settings(int(grp_id), set_type, True)
                await query.answer("ᴏɴ ✓")
            elif set_type == "fsub_limit":
                btn = [[
                    InlineKeyboardButton("1", callback_data=f"fsub_limit_set#1#{grp_id}"),
                    InlineKeyboardButton("3", callback_data=f"fsub_limit_set#3#{grp_id}"),
                    InlineKeyboardButton("5", callback_data=f"fsub_limit_set#5#{grp_id}"),
                    InlineKeyboardButton("10", callback_data=f"fsub_limit_set#10#{grp_id}"),
                ],[
                    InlineKeyboardButton("🔙 Back", callback_data=f"opnsetgrp#{grp_id}")
                ]]
                await query.message.edit_text("<b>ꜱᴇʟᴇᴄᴛ ꜰꜱᴜʙ ʀᴏᴛᴀᴛɪᴏɴ ʟɪᴍɪᴛ:</b>", reply_markup=InlineKeyboardMarkup(btn))
                return
            elif set_type == "fsub_pool":
                temp.SETTING_POOL[query.from_user.id] = int(grp_id)
                await query.message.edit_text("<b>ꜱᴇɴᴅ ᴄʜᴀɴɴᴇʟ ɪᴅꜱ / ᴜꜱᴇʀɴᴀᴍᴇꜱ ꜰᴏʀ ꜰꜱᴜʙ ᴘᴏᴏʟ (ᴄᴏᴍᴍᴀ ꜱᴇᴘᴀʀᴀᴛᴇᴅ):\nᴇx: <code>-1001234567890, @channel2, @channel3</code></b>")
                return
            
            settings = await get_settings(int(grp_id))
            if settings is not None:
                btn = await group_setting_buttons(int(grp_id))
                reply_markup = InlineKeyboardMarkup(btn)
                await query.message.edit_reply_markup(reply_markup)

        elif query.data.startswith("fsub_limit_set"):
            await query.answer()
            _, value, grp_id = query.data.split("#")
            await save_group_settings(int(grp_id), "fsub_limit", int(value))
            await query.answer(f"ꜰꜱᴜʙ ʟɪᴍɪᴛ ꜱᴇᴛ ᴛᴏ {value} ✅")
            btn = await group_setting_buttons(int(grp_id))
            await query.message.edit_text(generate_settings_text(await get_settings(int(grp_id)), query.message.chat.title), reply_markup=InlineKeyboardMarkup(btn))
        
        await query.answer(MSG_ALRT)
    except Exception as e:
        logger.exception(f"Callback Error: {e}")
        await query.answer("Something went wrong!", show_alert=True)


async def auto_filter(client, msg, spoll=False):
    try:
        clean_cache()
        user_id = msg.from_user.id if msg.from_user else 0
        now = time.time()
        
        # Rate Limiting: 2s
        if user_id in USER_COOLDOWN and now - USER_COOLDOWN[user_id] < 2:
            return
        USER_COOLDOWN[user_id] = now

        m = None
        if not spoll:
            message = msg
            if message.text.startswith("/") or re.findall(r"((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
                return
            
            search = message.text.lower().strip()
            if not search or len(search) > 100:
                return

            m = await message.reply_text(f"<b><i> 𝖲𝖾𝖺𝗋𝖼𝗁𝗂𝗇𝗀 𝖿𝗈𝗋 '{search}' 🔎</i></b>")
            
            # Refine search query
            find = search.split(" ")
            search = ""
            removes = ["in", "upload", "series", "full", "horror", "thriller", "mystery", "print", "file"]
            for x in find:
                if x not in removes:
                    search = search + x + " "
            search = re.sub(r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|bro|bruh|helo|that|find|dubbed|link|venum|film|undo|kitti|tharu|kittumo|movie|any(one)|with\ssubtitle(s)?)", "", search, flags=re.IGNORECASE)
            search = re.sub(r"[:']", "", search.replace("-", " "))
            search = re.sub(r"\s+", " ", search).strip()
            
            # Database Query (Single call per search)
            files, offset, total_results = await get_search_results(message.chat.id, search, offset=0, filter=True, max_results=1000)
            files = files[:300] # Cap search result dataset for memory
            
            settings = await get_settings(message.chat.id)
            if not files:
                if settings.get("spell_check"):
                    ai_sts = await m.edit('🤖 ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ...')
                    is_misspelled = await ai_spell_check(chat_id=message.chat.id, wrong_name=search)
                    if is_misspelled:
                        await ai_sts.delete()
                        message.text = is_misspelled
                        return await auto_filter(client, message)
                    await ai_sts.delete()
                else:
                    try: await m.delete()
                    except: pass
                return await advantage_spell_chok(client, message)
        else:
            message = msg.message.reply_to_message
            search, files, offset, total_results = spoll
            files = files[:300]
            m = await message.reply_text(f'🔎 sᴇᴀʀᴄʜɪɴɢ {search}', reply_to_message_id=message.id)
            settings = await get_settings(message.chat.id)
            await msg.message.delete()

        search = search.strip().lower()
        cache_key = hashlib.md5(f"{user_id}:{search}".encode()).hexdigest()[:8]
        if len(CACHE) > 100:
            CACHE.clear()
        
        CACHE[cache_key] = {
            "files": files, 
            "titles": get_titles(files),
            "langs": get_languages(files),
            "quals": get_qualities(files),
            "search": search,
            "time": time.time()
        }
        
        btn = get_next_markup(cache_key, "all", "all", "all", "all", files)
        
        # Poster logic optimized: limit to essential fields
        imdb = None
        if settings.get('imdb'):
            imdb = await get_posterx(search, file=(files[0]).file_name) if TMDB_POSTER else await get_poster(search, file=(files[0]).file_name)

        cap = f"<b>🏷 ᴛɪᴛʟᴇ : <code>{search}</code>\n🧱 ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ : <code>{total_results}</code>\n\n📝 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {message.from_user.mention}\n</b>"
        if imdb and settings.get('template'):
            try:
                imdb_data = imdb.copy()
                if 'plot' in imdb_data:
                    imdb_data['plot'] = imdb_data['plot'][:200]
                cap = settings['template'].format(**imdb_data)
            except Exception as e:
                logger.error(f"Template Error: {e}")

        sent = None
        markup = InlineKeyboardMarkup(btn)
        if imdb and imdb.get('poster'):
            sent = await message.reply_photo(photo=imdb.get('poster'), caption=cap, reply_markup=markup)
        else:
            sent = await message.reply_text(text=cap, reply_markup=markup, disable_web_page_preview=True)
        
        if m: await m.delete()
        if settings.get('auto_delete'):
            asyncio.create_task(_schedule_delete(sent, message, DELETE_TIME))
    except Exception as e:
        logger.exception(e)

async def ai_spell_check(chat_id, wrong_name):
    async def search_movie(wrong_name):
        search_results = imdb.search_movie(wrong_name)
        if not search_results or not hasattr(search_results, "titles"):
            return []
        movie_list = [movie.title for movie in search_results.titles]
        return movie_list
    movie_list = await search_movie(wrong_name)
    if not movie_list:
        return
    for _ in range(5):
        closest_match = process.extractOne(wrong_name, movie_list)
        if not closest_match or closest_match[1] <= 80:
            return
        movie = closest_match[0]
        files, _, _ = await get_search_results(chat_id=chat_id, query=movie, max_results=1000)
        if files:
            return movie
        movie_list.remove(movie)

async def advantage_spell_chok(client, message):
    mv_id = message.id
    search = message.text
    chat_id = message.chat.id
    settings = await get_settings(chat_id)
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", message.text, flags=re.IGNORECASE)
    query = query.strip() + " movie"
    try:
        movies = await get_poster(search, bulk=True)
    except Exception as e:
        logger.exception("get_poster failed for query=%s: %s", query, e)
        try:
            k = await message.reply(script.I_CUDNT.format(message.from_user.mention))
            await asyncio.sleep(60)
            try:
                await k.delete()
            except Exception:
                pass
        except Exception:
            pass
        try:
            await message.delete()
        except Exception:
            pass
        return
    if not movies:
        google = quote_plus(search)
        button = [[InlineKeyboardButton(
            "🔍 ᴄʜᴇᴄᴋ sᴘᴇʟʟɪɴɢ ᴏɴ ɢᴏᴏɢʟᴇ 🔍", url=f"https://www.google.com/search?q={google}")]]
        k = await message.reply_text(text=script.I_CUDNT.format(search), reply_markup=InlineKeyboardMarkup(button))
        await asyncio.sleep(60)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
        return
    user = message.from_user.id if message.from_user else 0
    buttons = [
        [InlineKeyboardButton(text=movie.title, callback_data=f"spol#{movie.imdb_id}#{user}")
         ] for movie in movies]

    buttons.append([InlineKeyboardButton(
        text="🚫 ᴄʟᴏsᴇ 🚫", callback_data='close_data')])
    d = await message.reply_text(text=script.CUDNT_FND.format(message.from_user.mention), reply_markup=InlineKeyboardMarkup(buttons), reply_to_message_id=message.id)
    await asyncio.sleep(60)
    await d.delete()
    try:
        await message.delete()
    except:
        pass
    
