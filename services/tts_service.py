import re
import edge_tts

def _rate_to_edge_percentage(rate: float) -> str:
    # rate 0.8 => -20%
    # rate 1.0 => +0%
    # rate 1.2 => +20%
    delta = int((rate - 1.0) * 100)
    return f"{delta:+d}%"

def _build_ssml(text: str, voice: str, rate: float = 1.0) -> str:
    safe_text = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )

    rate_value = _rate_to_edge_percentage(rate)
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
        f"<voice name='{voice}'><prosody rate='{rate_value}'>{safe_text}</prosody></voice>"
        "</speak>"
    )

async def text_to_speech_multivoice(
    script_text: str,
    is_dialogue: bool = False,
    speech_rate: float = 1.0
) -> bytes:
    voice_news = "en-US-AriaNeural"
    voice_speaker_a = "en-US-AriaNeural"
    voice_speaker_b = "en-US-GuyNeural"

    combined_audio = bytearray()

    if not is_dialogue:
        ssml = _build_ssml(script_text, voice_news, rate=speech_rate)
        communicate = edge_tts.Communicate(ssml)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                combined_audio.extend(chunk["data"])
        return bytes(combined_audio)

    lines = script_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^(A|B):\s*(.*)", line, re.IGNORECASE)
        if match:
            speaker, text = match.groups()
            chosen_voice = voice_speaker_a if speaker.upper() == "A" else voice_speaker_b
            chosen_rate = speech_rate
        else:
            text = line
            chosen_voice = voice_news
            chosen_rate = speech_rate

        ssml = _build_ssml(text, chosen_voice, rate=chosen_rate)
        communicate = edge_tts.Communicate(ssml)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                combined_audio.extend(chunk["data"])

    return bytes(combined_audio)