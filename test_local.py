import asyncio
from services.llm_service import generate_english_lesson
from services.tts_service import text_to_speech_bytes

async def run_test():
    print("⏳ Đang gọi LLM (Gemini) để sinh kịch bản tiếng Anh...")
    
    lesson_text = await generate_english_lesson()
    
    print("\n--- 🤖 NỘI DUNG AI SINH RA ---")
    print(lesson_text)
    print("------------------------------\n")
    
    print("⏳ Đang chuyển đổi văn bản thành âm thanh (Edge-TTS)...")
    # 2. Test chuyển text thành bytes MP3
    audio_bytes = await text_to_speech_bytes(lesson_text)
    
    # 3. Lưu thử ra file MP3 trên máy tính để nghe thử
    output_filename = "test_output.mp3"
    with open(output_filename, "wb") as f:
        f.write(audio_bytes)
        
    print(f"✅ Đã lưu thành công file âm thanh tại: {output_filename}")
    print("🎧 Bạn có thể mở file này trực tiếp trên máy tính để nghe thử giọng đọc!")

if __name__ == "__main__":
    asyncio.run(run_test())