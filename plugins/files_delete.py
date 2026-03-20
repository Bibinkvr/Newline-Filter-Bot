import re
import logging
from pyrogram import Client, filters
from info import DELETE_CHANNELS
from database.ia_filterdb import Media, Media2, unpack_new_file_id
logger = logging.getLogger(__name__)

media_filter = filters.document | filters.video | filters.audio


@Client.on_message(filters.chat(DELETE_CHANNELS) & media_filter)
async def deletemultiplemedia(bot, message):
    """Delete Multiple files from database"""

    media = getattr(message, message.media.value, None)
    if not media:
        return

    file_id, _ = unpack_new_file_id(media.file_id)
    
    # 1. Try deleting by _id (direct match)
    result = await Media.collection.delete_one({'_id': file_id})
    if not result.deleted_count and MULTIPLE_DB:
        result = await Media2.collection.delete_one({'_id': file_id})
        
    if result.deleted_count:
        logger.info('File successfully deleted from database by ID.')
        return

    # 2. Fallback: Try deleting by name and size (sanitized and raw)
    # Get sanitized name (same logic as ia_filterdb.py)
    file_name_sanitized = re.sub(r"[_\-\.#+$%^&*()!~`,;:\"'?/<>\[\]{}=|\\]", " ", str(media.file_name))
    file_name_sanitized = re.sub(r"\s+", " ", file_name_sanitized).strip()
    
    search_queries = [
        {'file_name': file_name_sanitized, 'file_size': media.file_size},
        {'file_name': media.file_name, 'file_size': media.file_size}
    ]

    for query in search_queries:
        result = await Media.collection.delete_many(query)
        if MULTIPLE_DB:
            res2 = await Media2.collection.delete_many(query)
            if res2.deleted_count:
                result.deleted_count += res2.deleted_count
        
        if result.deleted_count:
            logger.info(f'Deleted {result.deleted_count} files from database by name: {query["file_name"]}')
            return

    logger.info('File not found in database.')