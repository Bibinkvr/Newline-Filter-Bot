import re

with open('plugins/pmfilter.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Replace the inner buttons of the 'about' handler to remove source and donation
about_block_old = r"    elif query\.data == \"about\":\n        buttons = \[\[\n            InlineKeyboardButton\('‼️ ᴅɪꜱᴄʟᴀɪᴍᴇʀ ‼️', callback_data='disclaimer'\),\n            InlineKeyboardButton \('🪔 sᴏᴜʀᴄᴇ', callback_data='source'\),\n        \],\[\n            InlineKeyboardButton\('ᴅᴏɴᴀᴛɪᴏɴ 💰', callback_data='donation'\),\n        \],\[\n            InlineKeyboardButton\('⇋ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ⇋', callback_data='start'\)\n        \]\]"

about_block_new = """    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('‼️ ᴅɪꜱᴄʟᴀɪᴍᴇʀ ‼️', callback_data='disclaimer')
        ],[
            InlineKeyboardButton('⇋ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ⇋', callback_data='start')
        ]]"""
text = re.sub(about_block_old, about_block_new, text)

# 2. Remove "donation" handler
text = re.sub(r"    elif query\.data == \"donation\":[\s\S]*?(?=    elif query\.data == \"help\":)", "", text)

# 3. Remove "source" and "ref_point" handlers
text = re.sub(r"    elif query\.data == \"source\":[\s\S]*?(?=    elif query\.data == \"disclaimer\":)", "", text)

with open('plugins/pmfilter.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("pmfilter.py source and donation cleaned successfully")
