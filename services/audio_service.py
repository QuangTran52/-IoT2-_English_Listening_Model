import datetime
import random
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


async def generate_daily_audio() -> str:
    storage_dir = ensure_storage_dir()
    
    # 1. Xóa toàn bộ file MP3 cũ trong thư mục storage
    cleanup_old_mp3()

    # 2. Lấy thời gian thực theo múi giờ Việt Nam
    now_vn = datetime.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    day_of_week = now_vn.weekday()            # 0 (Thứ 2) -> 6 (Chủ Nhật)
    day_of_year = now_vn.timetuple().tm_yday  # Ngày thứ mấy trong năm (1-366)

    # 3. Chọn chủ đề tương ứng với ngày trong tuần
    topic = WEEKLY_TOPICS.get(day_of_week, "Daily conversation and greeting")

    # 4. Random hoàn toàn giữa dialogue và podcast
    chosen_type = DAILY_LESSON_TYPE
    if chosen_type == "random":
        chosen_type = random.choice(["dialogue", "podcast"])

    # 5. Tính toán tốc độ đọc dao động mượt mà theo ngày
    speech_rate = dynamic_speech_rate(base_rate=1.0, step=day_of_year)

    print(
        f"🚀 [Daily Audio] Đang tạo bài mới | Thứ {day_of_week + 2} | "
        f"Kiểu: {chosen_type} | Rate: {speech_rate} | Chủ đề: {topic}"
    )

    # 6. Gọi LLM sinh kịch bản
    result = await generate_smart_lesson(
        topic_detail=topic,
        cefr_level=DAILY_LEVEL,
        target_duration=DAILY_DURATION,
        lesson_type=chosen_type,
        variation_step=day_of_year
    )

    # 7. Chuyển kịch bản thành giọng nói MP3
    audio_bytes = await text_to_speech_multivoice(
        script_text=result["script"],
        is_dialogue=(chosen_type == "dialogue"),
        speech_rate=speech_rate
    )

    # 8. Lưu thành file current.mp3 mới
    out_file = storage_dir / "current.mp3"
    out_file.write_bytes(audio_bytes)

    print(f"✅ Daily audio saved successfully to: {out_file}")
    return str(out_file)