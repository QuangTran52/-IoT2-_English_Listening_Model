import datetime
import random
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (
    STORAGE_DIR,
    DAILY_LEVEL,
    DAILY_DURATION,
    DAILY_LESSON_TYPE,
)
from routers.lesson import WEEKLY_TOPICS
from services.llm_service import generate_smart_lesson
from services.tts_service import text_to_speech_multivoice
from services.variation_service import dynamic_speech_rate


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
            print(f"🗑️ Deleted old audio: {file.name}")
        except Exception as e:
            print(f"⚠️ Cannot delete {file.name}: {e}")


async def generate_daily_audio(
    custom_topic: str | None = None,
    force_random_topic: bool = False
) -> dict:
    """
    - Khi chạy tự động lúc 0h00: custom_topic=None, force_random_topic=False -> Lấy chủ đề theo Thứ.
    - Khi chạy Demo chen ngang: Có thể truyền custom_topic hoặc bốc ngẫu nhiên chủ đề khác.
    """
    storage_dir = ensure_storage_dir()
    cleanup_old_mp3()

    now_vn = datetime.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    # 1. Chọn chủ đề
    if custom_topic and custom_topic.strip():
        topic = custom_topic.strip()
    elif force_random_topic:
        topic = random.choice(list(WEEKLY_TOPICS.values()))
    else:
        topic = WEEKLY_TOPICS.get(now_vn.weekday(), "Daily conversation and greeting")

    # 2. Xử lý random giữa dialogue và podcast
    chosen_type = DAILY_LESSON_TYPE
    if chosen_type == "random":
        chosen_type = random.choice(["dialogue", "podcast"])

    # 3. Tính step dao động (0h00 dùng ngày trong năm, Demo dùng số ngẫu nhiên để thấy rõ sự khác biệt)
    if custom_topic or force_random_topic:
        step = random.randint(1, 365)
    else:
        step = now_vn.timetuple().tm_yday

    speech_rate = dynamic_speech_rate(base_rate=1.0, step=step)

    print(
        f"🚀 [Generate Audio] Kiểu: {chosen_type} | Rate: {speech_rate} | Chủ đề: {topic}"
    )

    # 4. Gọi LLM sinh kịch bản
    result = await generate_smart_lesson(
        topic_detail=topic,
        cefr_level=DAILY_LEVEL,
        target_duration=DAILY_DURATION,
        lesson_type=chosen_type,
        variation_step=step
    )

    # 5. Chuyển kịch bản thành giọng nói MP3
    audio_bytes = await text_to_speech_multivoice(
        script_text=result["script"],
        is_dialogue=(chosen_type == "dialogue"),
        speech_rate=speech_rate
    )

    # 6. Lưu đè thành file current.mp3 mới
    out_file = storage_dir / "current.mp3"
    out_file.write_bytes(audio_bytes)

    # 7. Cập nhật mã version (timestamp) để ESP32 phát hiện có file mới
    version_id = str(int(time.time()))
    (storage_dir / "version.txt").write_text(version_id, encoding="utf-8")

    print(f"✅ Saved new audio: {out_file} (Version: {version_id})")
    return {
        "file": str(out_file),
        "version": version_id,
        "topic": topic,
        "lesson_type": chosen_type,
        "speech_rate": speech_rate,
        "sentence_count": result.get("sentence_count", 0),
        "script": result["script"]
    }