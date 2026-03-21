import re

# 1. database/users_chats_db.py
with open('database/users_chats_db.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r"[ \t]*self\.verify_id = self\.db\.verify_id\n", "", text)
text = re.sub(r"[ \t]*'shortner':.*?,\n", "", text)
text = re.sub(r"[ \t]*'api':.*?,\n", "", text)
text = re.sub(r"[ \t]*'shortner_two':.*?,\n", "", text)
text = re.sub(r"[ \t]*'api_two':.*?,\n", "", text)
text = re.sub(r"[ \t]*'shortner_three':.*?,\n", "", text)
text = re.sub(r"[ \t]*'api_three':.*?,\n", "", text)
text = re.sub(r"[ \t]*'is_verify':.*?,\n", "", text)
text = re.sub(r"[ \t]*'verify_time':.*?,\n", "", text)
text = re.sub(r"[ \t]*'third_verify_time':.*?,\n", "", text)

# Remove all notcopy functions up to update_verify_id_info
pattern = r"    async def get_notcopy_user[\s\S]*?async def get_bot_setting"
text = re.sub(pattern, "    async def get_bot_setting", text)

with open('database/users_chats_db.py', 'w', encoding='utf-8') as f:
    f.write(text)


# 2. utils.py
with open('utils.py', 'r', encoding='utf-8') as f:
    text = f.read()

# remove get_shortlink
pattern = r"async def get_shortlink[\s\S]*?return link\n\n"
text = re.sub(pattern, "", text)

# remove verification string from  generate_settings_text
text = re.sub(r"✅️ <b><u>1sᴛ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ</u></b>.*?\n.*?\n.*?\n", "", text)
text = re.sub(r"✅️ <b><u>2ɴᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ</u></b>.*?\n.*?\n.*?\n", "", text)
text = re.sub(r"✅️ <b><u>𝟹ʀᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ</u></b>.*?\n.*?\n.*?\n", "", text)
text = re.sub(r"⏰ <b>2ɴᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ</b>.*?\n", "", text)
text = re.sub(r"⏰ <b>𝟹ʀᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ</b>.*?\n", "", text)

# remove is_verify button
pattern = r"            ],\[\n[ \t]*InlineKeyboardButton\('Vᴇʀɪғʏ'[\s\S]*?\],\n[ \t]*\["
text = re.sub(pattern, "            ],\n            [", text)

with open('utils.py', 'w', encoding='utf-8') as f:
    f.write(text)


# 3. plugins/commands.py
with open('plugins/commands.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the incoming verification tokenizer intercept logic
pattern = r"[ \t]*if len\(m\.command\) == 2 and m\.command\[1\]\.startswith\(\('notcopy', 'sendall'\)\):[\s\S]*?return[ \t]*$"
text = re.sub(pattern, "", text, flags=re.MULTILINE)

# Remove the verification generator logic in normal file request
# "if True:\n            try:\n... grp_id = int(grp_id)\n... user_verified = await db.is_user_verified(user_id) ... exceptions ... pass"
# Wait, this is hard using regex because it contains many elements. Let's do a strict match up to `# Now, await the file details task`
pattern = r"        user_id = m\.from_user\.id\n        if True:\n            try:\n                grp_id = int\(grp_id\)\n                user_verified.*?pass\n\n"
text = re.sub(pattern, "        user_id = m.from_user.id\n", text, flags=re.DOTALL)

# Delete the /verify command and handle_shortner_command blocks that follow it.
# Actually they are around line 1240. Let's use a safe regex that deletes from /verify to EOF or before next handler
pattern = r"@Client\.on_message\(filters\.command\(\"verify\"\).*?(?=@Client\.on_message|$)"
text = re.sub(pattern, "", text, flags=re.DOTALL)

# Remove the shortner functions
pattern = r"@Client\.on_message\(filters\.command\(\['shortner', 'shortner_two', 'shortner_three'\]\).*?(?=@Client\.on_message|$)"
text = re.sub(pattern, "", text, flags=re.DOTALL)

pattern = r"@Client\.on_message\(filters\.command\(\['api', 'api_two', 'api_three'\]\).*?(?=@Client\.on_message|$)"
text = re.sub(pattern, "", text, flags=re.DOTALL)

pattern = r"async def handle_shortner_command.*?await message\.reply_text\(f\"Successfully saved.*?\)\n\n"
text = re.sub(pattern, "", text, flags=re.DOTALL)

# Remove time limit commands
pattern = r"@Client\.on_message\(filters\.command\(\['third_verify_time', 'verify_time'\]\).*?(?=@Client\.on_message|$)"
text = re.sub(pattern, "", text, flags=re.DOTALL)

with open('plugins/commands.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("DB, Utils, and Commands cleaned!")
