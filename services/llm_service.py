import os
import re
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


def _sanitize_llm_script(raw_script: str, is_dialogue: bool) -> str:
    """Làm sạch kịch bản ngay sau khi LLM trả về"""
    # Xóa các khối ``` (nếu LLM bọc trong markdown code block)
    text = re.sub(r"```.*?```", "", raw_script, flags=re.DOTALL)
    text = text.replace("```", "")
    # Xóa các ghi chú cảm xúc/âm thanh trong ngoặc (...) hoặc [...]
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    # Xóa ký tự markdown *, #, _
    text = re.sub(r"[\*\#_]", "", text)

    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if is_dialogue:
            # Chỉ giữ lại các dòng hội thoại thực sự hoặc dòng có nội dung
            cleaned_lines.append(line)
        else:
            # Nếu là podcast, xóa các chữ "Host:" hoặc "Narrator:" ở đầu dòng
            line = re.sub(r"^(Host|Narrator|Podcast|Speaker)\s*:\s*", "", line, flags=re.IGNORECASE)
            if line:
                cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


async def generate_smart_lesson(
    topic_detail: str,
    cefr_level: str = "A2",
    target_duration: str = "1 min",
    lesson_type: str = "dialogue",
    variation_step: int = 0
) -> dict:
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

    is_dialogue = (lesson_type == "dialogue")

    if is_dialogue:
        system_instruction = (
            "You are a precise English language teacher and dialogue writer. "
            "Output strictly plain text dialogue lines starting with 'A:' and 'B:'. "
            "Do NOT include markdown, asterisks, stage directions, sound effects, parentheses, or intro/outro commentary."
        )
        user_prompt = (
            f"Write a short, realistic English daily conversation focusing strictly on: '{topic_detail}'.\n"
            f"- CEFR Level: {cefr_level}.\n"
            f"- Required approximate sentence count: {dynamic_count} lines.\n"
            f"- Keep it natural and engaging.\n"
            f"- Strictly use this exact format without any extra text:\n"
            f"A: Hello, how can I help you today?\n"
            f"B: Hi, I would like to order a cup of coffee.\n"
        )
    else:
        system_instruction = (
            "You are a professional English podcast speaker. "
            "Output ONLY the spoken sentences as continuous plain text. "
            "Do NOT include speaker labels (like 'Host:'), sound effects, markdown, asterisks, or stage directions."
        )
        user_prompt = (
            f"Write a short English podcast monologue about: '{topic_detail}'.\n"
            f"- CEFR Level: {cefr_level}.\n"
            f"- Required approximate sentence count: {dynamic_count} sentences.\n"
            f"- Keep pacing natural and interesting, written strictly as spoken words only.\n"
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
                clean_script = _sanitize_llm_script(response.text, is_dialogue)
                return {
                    "script": clean_script,
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
                    clean_script = _sanitize_llm_script(result_text, is_dialogue)
                    return {
                        "script": clean_script,
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