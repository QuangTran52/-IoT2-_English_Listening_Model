import os
from dotenv import load_dotenv

# Load các biến từ file .env lên
load_dotenv()

# Lấy API Key ra sử dụng trong code
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")