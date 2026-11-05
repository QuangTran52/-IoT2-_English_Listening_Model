import os
import asyncio
from google import genai
from openai import OpenAI
from config import GEMINI_API_KEY

# Khởi tạo Gemini Client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Khởi tạo Groq Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

async def generate_smart_lesson(
    topic_detail: str, 
    cefr_level: str = "A2", 
    target_duration: str = "1 min", 
    lesson_type: str = "dialogue"
) -> dict:
    
    length_mapping = {
        "1 min": "khoảng 4-5 câu (tương đương 70-90 từ)",
        "1.5 min": "khoảng 8-10 câu (tương đương 140-170 từ)",
        "1.75 min": "khoảng 12-14 câu (tương đương 200-230 từ)",
        "2 min": "khoảng 16-18 câu (tương đương 260-300 từ)"
    }
    length_constraint = length_mapping.get(target_duration, "khoảng 5 câu")

    if lesson_type == "dialogue":
        system_instruction = "You are a precise English language teacher and dialogue writer. Output strictly the requested format without extra text."
        user_prompt = (
            f"Write a short, realistic English daily conversation focusing strictly on: '{topic_detail}'.\n"
            f"- CEFR Level: {cefr_level}.\n"
            f"- Length: {length_constraint}.\n"
            f"- Format:\n"
            f"A: [line]\n"
            f"B: [line]\n"
        )
    else:
        system_instruction = "You are a professional English podcast writer. Output continuous plain text only."
        user_prompt = (
            f"Write a short English podcast script about: '{topic_detail}'.\n"
            f"- CEFR Level: {cefr_level}.\n"
            f"- Length: {length_constraint}.\n"
        )

    # --- TẦNG 1: THỬ GEMINI CORE ---
    for model_name in ['gemini-3.8-flash', 'gemini-2.5-flash']:
        try:
            print(f"🔄 [Gemini Engine] Đang gọi '{model_name}'...")
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_client.models.generate_content,
                    model=model_name,
                    contents=f"{system_instruction}\n\n{user_prompt}",
                ),
                timeout=5.0
            )
            if response and response.text:
                print(f"✅ Thành công với Gemini '{model_name}'!")
                return {"script": response.text.strip(), "level": cefr_level, "duration": target_duration}
        except Exception as e:
            print(f"⚠️ Gemini '{model_name}' bận/lỗi: {e}")

    print("🔄 Gemini quá tải. Chuyển sang hạ tầng Groq với các model sẵn có...")

    # --- TẦNG 2: THỬ CÁC MODEL SINH TEXT KHỚP VỚI TÀI KHOẢN GROQ CỦA BẠN ---
    # Ưu tiên Qwen 27B và các model OSS đang active trên tài khoản của bạn
    groq_text_models = [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "allam-2-7b"
    ]

    for g_model in groq_text_models:
        try:
            print(f"🔄 [Groq Engine] Đang gọi model '{g_model}'...")
            
            completion = await asyncio.wait_for(
                asyncio.to_thread(
                    groq_client.chat.completions.create,
                    model=g_model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=400
                ),
                timeout=6.0
            )
            
            result_text = completion.choices[0].message.content.strip()
            if result_text:
                print(f"✅ Thành công với Groq model '{g_model}'!")
                return {"script": result_text, "level": cefr_level, "duration": target_duration}
                
        except Exception as e:
            print(f"⚠️ Groq model '{g_model}' gặp sự cố: {e}")

    # --- TẦNG 3: BẢO VỆ TUYỆT ĐỐI (SAFE FALLBACK) ---
    print("❌ Tất cả các AI Engine ngoại tuyến. Dùng bộ sinh kịch bản động an toàn.")
    fallback_script = (
        f"A: Hello! Let's practice English about {topic_detail}.\n"
        f"B: That sounds wonderful. Let's start right now."
    )
    return {
        "script": fallback_script,
        "level": cefr_level,
        "duration": target_duration
    }