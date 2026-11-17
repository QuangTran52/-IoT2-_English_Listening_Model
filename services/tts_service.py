import re
import edge_tts


def _rate_to_edge_percentage(rate: float) -> str:
    # rate 0.8 => -20%, rate 1.0 => +0%, rate 1.2 => +20%
    delta = int(round((rate - 1.0) * 100))
    return f"{delta:+d}%"


def _clean_spoken_text(text: str) -> str:
    """Làm sạch các ký tự markdown, ngoặc chú thích hoặc gạch chéo trước khi đọc"""
    # Xóa nội dung trong ngoặc vuông [SFX...] hoặc ngoặc tròn (laughing...)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    # Xóa các ký tự markdown *, #, _, `, ~, //
    text = text.replace("//", " ")
    text = re.sub(r"[\*\#_`~]", "", text)
    # Gộp nhiều khoảng trắng thành 1
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def text_to_speech_multivoice(
    script_text: str,
    is_dialogue: bool = False,
    speech_rate: float = 1.0
) -> bytes:
    voice_news = "en-US-AriaNeural"
    voice_speaker_a = "en-US-AriaNeural"
    voice_speaker_b = "en-US-GuyNeural"

    rate_str = _rate_to_edge_percentage(speech_rate)
    combined_audio = bytearray()

    if not is_dialogue:
        clean_text = _clean_spoken_text(script_text)
        # Bỏ các nhãn kiểu "Host:" hoặc "Podcast:" nếu LLM lỡ thêm vào đầu câu
        clean_text = re.sub(r"^(Host|Narrator|Speaker|Podcast):\s*", "", clean_text, flags=re.IGNORECASE)
        if clean_text:
            communicate = edge_tts.Communicate(text=clean_text, voice=voice_news, rate=rate_str)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    combined_audio.extend(chunk["data"])
        return bytes(combined_audio)

    lines = script_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Bỏ dấu * hoặc - ở đầu dòng (ví dụ: "**A:** Hello" -> "A: Hello")
        line_clean = re.sub(r"^[\*\-\s]+", "", line)

        match = re.match(r"^(A|B|Person A|Person B|Speaker A|Speaker B)\s*:\s*(.*)", line_clean, re.IGNORECASE)
        if match:
            speaker_Raw, raw_content = match.groups()
            speaker = "A" if speaker_Raw.upper().endswith("A") else "B"
            chosen_voice = voice_speaker_a if speaker == "A" else voice_speaker_b
            text = _clean_spoken_text(raw_content)
        else:
            chosen_voice = voice_news
            text = _clean_spoken_text(line_clean)

        if not text:
            continue

        communicate = edge_tts.Communicate(text=text, voice=chosen_voice, rate=rate_str)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                combined_audio.extend(chunk["data"])

    return bytes(combined_audio)