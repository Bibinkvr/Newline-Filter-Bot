try:
    import pyrogram
    print("pyrogram ok")
except ImportError:
    print("pyrogram missing")

try:
    import pymongo
    print("pymongo ok")
except ImportError:
    print("pymongo missing")

try:
    import motor
    print("motor ok")
except ImportError:
    print("motor missing")

try:
    import dotenv
    print("dotenv ok")
except ImportError:
    print("dotenv missing")

try:
    import aiohttp
    print("aiohttp ok")
except ImportError:
    print("aiohttp missing")
