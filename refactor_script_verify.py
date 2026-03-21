import re

with open('Script.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove VERIFY_COMPLETE_TEXT
text = re.sub(r"    VERIFY_COMPLETE_TEXT = \"\"\"[\s\S]*?(?=    SECOND_VERIFY_COMPLETE_TEXT)", "", text)
# Remove SECOND_VERIFY_COMPLETE_TEXT
text = re.sub(r"    SECOND_VERIFY_COMPLETE_TEXT = \"\"\"[\s\S]*?(?=    THIRDT_VERIFY_COMPLETE_TEXT)", "", text)
# Remove THIRDT_VERIFY_COMPLETE_TEXT
text = re.sub(r"    THIRDT_VERIFY_COMPLETE_TEXT= \"\"\"[\s\S]*?(?=    VERIFICATION_TEXT)", "", text)

# Remove VERIFICATION_TEXT
text = re.sub(r"    VERIFICATION_TEXT = \"\"\"[\s\S]*?(?=    SECOND_VERIFICATION_TEXT)", "", text)
# Remove SECOND_VERIFICATION_TEXT
text = re.sub(r"    SECOND_VERIFICATION_TEXT = \"\"\"[\s\S]*?(?=    THIRDT_VERIFICATION_TEXT)", "", text)
# Remove THIRDT_VERIFICATION_TEXT
text = re.sub(r"    THIRDT_VERIFICATION_TEXT = \"\"\"[\s\S]*?(?=    HOW_TO_VERIFY)", "", text)

# Remove SOURCE_TXT
text = re.sub(r"    SOURCE_TXT =\"\"\"[\s\S]*?Strictly Prohibited\.\\n\"\"\"\n*", "", text)
text = re.sub(r"    SOURCE_TXT = \"\"\"[\s\S]*?Strictly Prohibited\.\\n\"\"\"\n*", "", text)

# Remove MOVIEBOT_DONATION
text = re.sub(r"    MOVIEBOT_DONATION = DONATE_TXT = \"\"\" \"\"\"\n*", "", text)

# Remove /verify from ADMIN_CMD
text = re.sub(r"• /verify - <code>.*?</code>\n?", "", text)

with open('Script.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Script.py cleaned successfully!")
