import re

# 1. info.py
with open('info.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r"IS_VERIFY = is_enabled\('IS_VERIFY', False\).*?\n", "", text)
text = re.sub(r"VERIFY_IMG = environ\.get\(\"VERIFY_IMG\".*?\n", "", text)
text = re.sub(r"SHORTENER_API\d* = environ\.get.*?#.*?\n", "", text)
text = re.sub(r"SHORTENER_WEBSITE\d* = environ\.get.*?#.*?\n", "", text)
text = re.sub(r"TWO_VERIFY_GAP = int\(\w+\.get\('TWO_VERIFY_GAP'.*?\n", "", text)
text = re.sub(r"THREE_VERIFY_GAP = int\(\w+\.get\('THREE_VERIFY_GAP'.*?\n([ \t]*\n)*", "", text)

with open('info.py', 'w', encoding='utf-8') as f:
    f.write(text)

# 2. requirements.txt
with open('requirements.txt', 'r', encoding='utf-8') as f:
    text = f.read()
text = re.sub(r"pyshorteners\n?", "", text)
with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("info.py and requirements.txt processed")
