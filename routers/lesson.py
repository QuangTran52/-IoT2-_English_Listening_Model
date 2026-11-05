from fastapi import APIRouter, Query
from fastapi.responses import Response
from services.llm_service import generate_smart_lesson
from services.tts_service import text_to_speech_multivoice
import datetime

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
    hour: int = Query(8, description="Giờ hiện tại do RTC trên ESP32 gửi lên (0-23)"),
    user_action: str = Query("normal", description="'normal': bình thường, 'too_hard': user bấm nút báo khó/đổi bài"),
    day_of_week: int = Query(None, description="Thứ trong tuần (0-6). Nếu để trống sẽ lấy ngày hiện tại của server")
):
    """
    API thông minh cho ESP32 / Client gọi vào:
    1. Tự động chọn chủ đề theo lịch trình tuần nếu không truyền vào.
    2. Xác định CEFR theo khung giờ trong ngày (Sáng: A2, Chiều/Tối: B1/B2).
    3. Xử lý nút bấm phần cứng (nếu quá khó -> tự động hạ cấp độ).
    4. Trả về luồng Audio MP3 kèm metadata tốc độ phát qua Header.
    """
    
    # --- 1. TỰ ĐỘNG CHỌN CHỦ ĐỀ THEO LỊCH TRÌNH ---
    if day_of_week is None:
        # Lấy ngày hiện tại của hệ thống server (0: Thứ 2, ..., 6: Chủ Nhật)
        day_of_week = datetime.datetime.now().weekday()
    
    topic = WEEKLY_TOPICS.get(day_of_week, "Daily conversation and greeting")

    # --- 2. XÁC ĐỊNH CEFR & THỜI LƯỢNG THEO KHUNG GIỜ ---
    if 5 <= hour < 12:
        base_cefr = "A2"
        target_duration = "1 min"
        speed_factor = 0.85  # Hơi chậm cho buổi sáng
    elif 12 <= hour < 18:
        base_cefr = "B1"
        target_duration = "1.5 min"
        speed_factor = 1.0   # Tốc độ chuẩn
    else:
        base_cefr = "B2"
        target_duration = "1.75 min"
        speed_factor = 1.15  # Thử thách tốc độ buổi tối

    # --- 3. XỬ LÝ PHẢN HỒI NÚT BẤM (HẠ ĐỘ KHÓ) ---
    if user_action == "too_hard":
        cefr_levels = ["A1", "A2", "B1", "B2", "C1"]
        current_idx = cefr_levels.index(base_cefr) if base_cefr in cefr_levels else 1
        new_idx = max(0, current_idx - 1)
        final_cefr = cefr_levels[new_idx]
        target_duration = "1 min"
    else:
        final_cefr = base_cefr

    # --- 4. GỌI LLM SINH KỊCH BẢN ---
    lesson_data = await generate_smart_lesson(
        topic_detail=topic,
        cefr_level=final_cefr,
        target_duration=target_duration,
        lesson_type="dialogue"
    )
    
    script_text = lesson_data["script"]
    print(f"📖 [Server Log] Ngày thứ: {day_of_week} | Giờ: {hour}h | Cấp độ: {final_cefr} | Chủ đề: {topic}")
    print(f"📝 Nội dung:\n{script_text}\n")

    # --- 5. CHUYỂN ĐỔI THÀNH ÂM THANH (TTS) ---
    audio_bytes = await text_to_speech_multivoice(script_text, is_dialogue=True)

    # --- 6. TRẢ VỀ DỮ LIỆU MP3 KÈM HEADER METADATA ---
    headers = {
        "X-CEFR-Level": final_cefr,
        "X-Playback-Speed": str(speed_factor),
        "X-Lesson-Topic": topic
    }
    
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)