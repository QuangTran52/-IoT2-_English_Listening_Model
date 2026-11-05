import edge_tts
import io
import re

async def text_to_speech_multivoice(script_text: str, is_dialogue: bool = False) -> bytes:
    """
    Nếu là dialogue: tách các dòng A: và B: để đọc bằng 2 giọng khác nhau.
    Nếu là news/podcast: đọc toàn bộ bằng 1 giọng cố định.
    """
    # Các cấu hình giọng đọc
    voice_news = "en-US-AriaNeural"      # Giọng cho News/Podcast
    voice_speaker_a = "en-US-AriaNeural" # Giọng nhân vật A
    voice_speaker_b = "en-US-GuyNeural"  # Giọng nhân vật B (Nam)
    
    combined_audio = bytearray()

    if not is_dialogue:
        # Trường hợp 1: News / Podcast (Dùng 1 giọng duy nhất)
        communicate = edge_tts.Communicate(script_text, voice_news)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                combined_audio.extend(chunk["data"])
    else:
        # Trường hợp 2: Dialogue (Tách dòng và đổi giọng linh hoạt)
        lines = script_text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Kiểm tra xem dòng có theo định dạng "A: ..." hoặc "B: ..." không
            match = re.match(r"^(A|B):\s*(.*)", line, re.IGNORECASE)
            if match:
                speaker, text = match.groups()
                # Chọn giọng dựa vào nhân vật (A hoặc B)
                chosen_voice = voice_speaker_a if speaker.upper() == "A" else voice_speaker_b
            else:
                # Fallback nếu dòng không đúng chuẩn
                text = line
                chosen_voice = voice_news

            # Render audio cho riêng câu thoại đó (đã được lọc bỏ chữ "A: / B:")
            communicate = edge_tts.Communicate(text, chosen_voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    combined_audio.extend(chunk["data"])
                    
    return bytes(combined_audio)