with open('Script.py', 'r', encoding='utf-8', errors='surrogateescape') as f:
    text = f.read()

start_idx = text.find('    DISCLAIMER_TXT = """')
end_idx = text.find('"""\n\n    MOVIEBOT_DONATION', start_idx)

if start_idx != -1 and end_idx != -1:
    new_disclaimer = '''    DISCLAIMER_TXT = """
<blockquote>This bot aggregates and indexes content that is already publicly available on the internet or shared by third parties on Telegram. It does not host or upload any files directly.

All materials accessible through this bot are sourced from existing Telegram channels or external public platforms to improve search efficiency and user access.

If you are a copyright owner and believe any content violates your rights, please contact the respective source or Telegram for removal. This bot does not claim ownership of any indexed content.</blockquote>'''
    text = text[:start_idx] + new_disclaimer + text[end_idx:]
    with open('Script.py', 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(text)
    print("Replaced successfully.")
else:
    print(f"Failed to find indices. Start: {start_idx}, End: {end_idx}")
