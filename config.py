import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# local default: storage/audio
# Railway default nếu mount volume /data thì nên set STORAGE_DIR=/data/audio
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage/audio")

DAILY_TOPIC = os.getenv("DAILY_TOPIC", "daily routines at school")
DAILY_LEVEL = os.getenv("DAILY_LEVEL", "A2")
DAILY_DURATION = os.getenv("DAILY_DURATION", "1 min")
DAILY_LESSON_TYPE = "random"