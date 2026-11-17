import datetime
import random
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from fastapi.responses import Response

from services.llm_service import generate_smart_lesson
from services.tts_service import text_to_speech_multivoice
from services.variation_service import dynamic_speech_rate

router = APIRouter(prefix="/lesson", tags=["Lesson"])

# Danh sách chủ đề xoay vòng theo ngày trong tuần (0: Thứ Hai -> 6: Chủ Nhật)
WEEKLY_TOPICS = {
    0: "Ordering food and drinks at a cozy restaurant",
    1: "Asking for directions and navigating a new city",
    2: "Checking in at a hotel reception and requesting room services",
    3: "Shopping for clothes, asking for sizes and discussing prices",
    4: "Talking about hobbies, weekend plans, and casual interests",
    5: "Making a doctor's appointment and describing common symptoms",
    6: "Small talk with colleagues about workplace projects and coffee breaks"
}


@router.get("/get-audio")
async def get_lesson_audio(
    hour: int = Query(8, description="Giờ hiện tại do RTC/NTP trên ESP32 gửi lên (0-23)"),
    user_action: str = Query("normal", description="'normal': bình thường, 'too_hard': user bấm nút báo khó/đổi bài"),
    day_of_week: int | None = Query(None, description="Thứ trong tuần (0-6). Nếu để trống sẽ lấy ngày hiện tại theo giờ VN"),
    lesson_type: str = Query("random", description="'dialogue', 'podcast', hoặc 'random'")
):
    """
    API thông minh cho ESP32 / Client gọi trực tiếp:
    1. Tự động chọn chủ đề theo lịch trình tuần (múi giờ Asia/Ho_Chi_Minh).
    2. Xác định CEFR & tốc độ gốc theo khung giờ trong ngày (Sáng: A2, Chiều: B1, Tối: B2).
    3. Xử lý nút bấm phần cứng (nếu quá khó -> tự động hạ cấp độ & giảm tốc độ).
    4. Dao động số câu và tốc độ đọc tự nhiên qua variation_service.
    5. Trả về luồng Audio MP3 kèm metadata qua Header.
    """
    now_vn = datetime.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    # --- 1. TỰ ĐỘNG CHỌN CHỦ ĐỀ THEO LỊCH TRÌNH ---
    if day_of_week is None:
        day_of_week = now_vn.weekday()

    topic = WEEKLY_TOPICS.get(day_of_week, "Daily conversation and greeting")

    # --- 2. XÁC ĐỊNH CEFR & TỐC ĐỘ GỐC THEO KHUNG GIỜ ---
    if 5 <= hour < 12:
        base_cefr = "A2"
        target_duration = "1 min"
        base_speed = 0.90   # Hơi chậm cho buổi sáng
    elif 12 <= hour < 18:
        base_cefr = "B1"
        target_duration = "1.5 min"
        base_speed = 1.0    # Tốc độ chuẩn buổi chiều
    else:
        base_cefr = "B2"
        target_duration = "1.75 min"
        base_speed = 1.10   # Thử thách tốc độ buổi tối

    # --- 3. XỬ LÝ PHẢN HỒI NÚT BẤM (HẠ ĐỘ KHÓ) ---
    if user_action == "too_hard":
        cefr_levels = ["A1", "A2", "B1", "B2", "C1"]
        current_idx = cefr_levels.index(base_cefr) if base_cefr in cefr_levels else 1
        new_idx = max(0, current_idx - 1)
        final_cefr = cefr_levels[new_idx]
        target_duration = "1 min"
        base_speed = max(0.80, base_speed - 0.10)
    else:
        final_cefr = base_cefr

    # --- 4. XỬ LÝ LOẠI BÀI HỌC & BƯỚC DAO ĐỘNG (VARIATION STEP) ---
    chosen_type = lesson_type
    if chosen_type == "random":
        chosen_type = random.choice(["dialogue", "podcast"])

    # Kết hợp ngày trong năm và giờ hiện tại để tạo step dao động tự nhiên
    variation_step = now_vn.timetuple().tm_yday + hour

    final_speech_rate = dynamic_speech_rate(
        base_rate=base_speed,
        step=variation_step,
        spread=0.12,
        phase=0.25
    )

    # --- 5. GỌI LLM SINH KỊCH BẢN ---
    lesson_data = await generate_smart_lesson(
        topic_detail=topic,
        cefr_level=final_cefr,
        target_duration=target_duration,
        lesson_type=chosen_type,
        variation_step=variation_step
    )

    script_text = lesson_data["script"]
    print(
        f"📖 [Server Log] Thứ: {day_of_week + 2} | Giờ: {hour}h | "
        f"Cấp độ: {final_cefr} | Kiểu: {chosen_type} | Rate: {final_speech_rate} | Chủ đề: {topic}"
    )
    print(f"📝 Nội dung:\n{script_text}\n")

    # --- 6. CHUYỂN ĐỔI THÀNH ÂM THANH (TTS) ---
    audio_bytes = await text_to_speech_multivoice(
        script_text=script_text,
        is_dialogue=(chosen_type == "dialogue"),
        speech_rate=final_speech_rate
    )

    # --- 7. TRẢ VỀ DỮ LIỆU MP3 KÈM HEADER METADATA ---
    headers = {
        "X-CEFR-Level": final_cefr,
        "X-Lesson-Type": chosen_type,
        "X-Playback-Speed": str(final_speech_rate),
        "X-Sentence-Count": str(lesson_data.get("sentence_count", 0)),
        "X-Lesson-Topic": topic
    }

    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)