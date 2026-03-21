import codecs
import re

with codecs.open('plugins/commands.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Unindent force sub block
target_fsub = r"        if not await db\.has_premium_access\(message\.from_user\.id\): \n((?:            .*\n)+)"
def unindent_block(match):
    block = match.group(1)
    # remove 4 spaces from each line
    unindented = re.sub(r'^ {4}', '', block, flags=re.MULTILINE)
    return unindented

text = re.sub(target_fsub, unindent_block, text)

# 2. Unindent verification block
target_verify = r"        if not await db\.has_premium_access\(user_id\):\n((?:            .*\n)+)"
text = re.sub(target_verify, unindent_block, text)

# 3. Replace stream_buttons
target_stream_btn = r"async def stream_buttons\(user_id: int, file_id: str\):\n(?:    .*\n)+"
new_stream_btn = """async def stream_buttons(user_id: int, file_id: str):
    return [[InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]]
"""
text = re.sub(target_stream_btn, new_stream_btn, text)

with codecs.open('plugins/commands.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("commands.py modified.")

# Modify pmfilter.py
with codecs.open('plugins/pmfilter.py', 'r', encoding='utf-8') as f:
    pm_text = f.read()

target_stream_logic = r"    elif MoviebotData\.startswith\(\"generate_stream_link\"\):.*?        await moviebot_msg\.delete\(\)\n"
pm_text = re.sub(target_stream_logic, "", pm_text, flags=re.DOTALL)

with codecs.open('plugins/pmfilter.py', 'w', encoding='utf-8') as f:
    f.write(pm_text)

print("pmfilter.py modified.")
