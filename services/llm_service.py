import os
import asyncio

from google import genai
from openai import OpenAI

from config import GEMINI_API_KEY
from services.variation_service import dynamic_sentence_count

# Khởi tạo Gemini Client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Khởi tạo Groq Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
groq_client = None
if GROQ_API_KEY:
    groq_client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

async def generate_smart_lesson(
    topic_detail: str,
    cefr_level: str = "A2",
    target_duration: str = "1 min",
    lesson_type: str = "dialogue",
    variation_step: int = 0
) -> dict:
    # Mức độ cơ bản dựa theo target_duration
    base_sentence_map = {
        "1 min": 6,
        "1.5 min": 8,
        "1.75 min": 10,
        "2 min": 12
    }
    base_sentence = base_sentence_map.get(target_duration, 6)

    dynamic_count = dynamic_sentence_count(
        base_count=base_sentence,
        step=variation_step,
        spread=2,
        phase=0.2
    )

    # Tạo prompt
    if lesson_type == "dialogue":
        system_instruction = (
            "You are a precise English language teacher and dialogue writer. "
            "Output strictly the requested format without extra text."
        )
        user_prompt = (
            f"Write a short, realistic English daily conversation focusing strictly on: '{topic_detail}'.\n"
            f"- CEFR Level: {cefr_level}.\n"
            f"- Required approximate sentence count: {dynamic_count} sentences.\n"
            f"- Keep it natural and engaging, not too long.\n"
            f"- Format:\n"
            f"A: [line]\n"
            f"B: [line]\n"
        )
    else:
        system_instruction = (
            "You are a professional English podcast writer. "
            "Output continuous plain text only."
        )
        user_prompt = (
            f"Write a short English podcast script about: '{topic_detail}'.\n"
            f"- CEFR Level: {cefr_level}.\n"
            f"- Required approximate sentence count: {dynamic_count} sentences.\n"
            f"- Keep pacing natural and interesting.\n"
        )

    # Tầng 1: Gemini
    gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    for model_name in gemini_models:
        try:
            print(f"🔄 [Gemini Engine] Gọi '{model_name}'...")
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_client.models.generate_content,
                    model=model_name,
                    contents=f"{system_instruction}\n\n{user_prompt}",
                ),
                timeout=10.0
            )

            if response and getattr(response, "text", None):
                print(f"✅ Thành công với Gemini '{model_name}'")
                return {
                    "script": response.text.strip(),
                    "level": cefr_level,
                    "duration": target_duration,
                    "sentence_count": dynamic_count
                }

        except Exception as e:
            print(f"⚠️ Gemini '{model_name}' lỗi: {e}")

    # Tầng 2: Groq
    if groq_client:
        groq_models = list(dict.fromkeys([
            os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "openai/gpt-oss-20b",
            "meta-llama/llama-4-scout-17b-16e-instruct"
        ]))

        for g_model in groq_models:
            try:
                print(f"🔄 [Groq Engine] Gọi '{g_model}'...")
                completion = await asyncio.wait_for(
                    asyncio.to_thread(
                        groq_client.chat.completions.create,
                        model=g_model,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.4,
                        max_tokens=500
                    ),
                    timeout=12.0
                )

                result_text = completion.choices[0].message.content.strip()
                if result_text:
                    print(f"✅ Thành công với Groq '{g_model}'")
                    return {
                        "script": result_text,
                        "level": cefr_level,
                        "duration": target_duration,
                        "sentence_count": dynamic_count
                    }

            except Exception as e:
                print(f"⚠️ Groq '{g_model}' lỗi: {e}")

    # Fallback an toàn
    fallback_script = (
        f"A: Hello! Let's learn about {topic_detail}.\n"
        f"B: Great! We can practice together.\n"
        f"A: Today we will focus on this topic.\n"
        f"B: Nice! Let's keep learning step by step."
    )

    return {
        "script": fallback_script,
        "level": cefr_level,
        "duration": target_duration,
        "sentence_count": dynamic_count
    }