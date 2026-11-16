from pathlib import Path

from config import (
    STORAGE_DIR,
    DAILY_TOPIC,
    DAILY_LEVEL,
    DAILY_DURATION,
    DAILY_LESSON_TYPE,
)
from services.llm_service import generate_smart_lesson
from services.tts_service import text_to_speech_multivoice


def ensure_storage_dir() -> Path:
    storage_dir = Path(STORAGE_DIR)
    if not storage_dir.is_absolute():
        storage_dir = Path(__file__).resolve().parent.parent / storage_dir

    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def cleanup_old_mp3() -> None:
    storage_dir = ensure_storage_dir()
    for file in storage_dir.glob("*.mp3"):
        try:
            file.unlink()
            print(f"🗑️ Deleted: {file.name}")
        except Exception as e:
            print(f"⚠️ Cannot delete {file.name}: {e}")


async def generate_daily_audio() -> str:
    storage_dir = ensure_storage_dir()
    cleanup_old_mp3()

    result = await generate_smart_lesson(
        topic_detail=DAILY_TOPIC,
        cefr_level=DAILY_LEVEL,
        target_duration=DAILY_DURATION,
        lesson_type=DAILY_LESSON_TYPE,
        variation_step=1
    )

    audio_bytes = await text_to_speech_multivoice(
        script_text=result["script"],
        is_dialogue=(DAILY_LESSON_TYPE == "dialogue"),
        speech_rate=1.0
    )

    out_file = storage_dir / "current.mp3"
    out_file.write_bytes(audio_bytes)

    print(f"✅ Daily audio saved to: {out_file}")
    return str(out_file)