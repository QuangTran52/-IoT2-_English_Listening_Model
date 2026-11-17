import random
from pathlib import Path
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from config import STORAGE_DIR
from routers.lesson import router as lesson_router
from services.audio_service import generate_daily_audio
from services.llm_service import generate_smart_lesson
from services.tts_service import text_to_speech_multivoice
from services.variation_service import dynamic_speech_rate

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        storage_dir = Path(STORAGE_DIR)
        if not storage_dir.is_absolute():
            storage_dir = Path(__file__).resolve().parent / storage_dir

        if not (storage_dir / "current.mp3").exists():
            print("🔄 No daily audio found yet; generating on startup...")
            await generate_daily_audio()

        # Lịch tự động 0h00 mỗi ngày (chế độ bình thường)
        scheduler.add_job(
            generate_daily_audio,
            trigger=CronTrigger(
                hour=0,
                minute=0,
                second=0,
                timezone=ZoneInfo("Asia/Ho_Chi_Minh")
            ),
            id="daily_audio_job",
            replace_existing=True
        )
        scheduler.start()
        print("✅ Scheduler started; daily audio will generate at 00:00 Asia/Ho_Chi_Minh")
        yield
    finally:
        scheduler.shutdown()
        print("✅ Scheduler shutdown")


app = FastAPI(
    title="IoT English Listening Device API",
    description="Backend chính thức cho thiết bị học tiếng Anh IoT",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(lesson_router)
app.state.lesson_counter = 0


class LessonRequest(BaseModel):
    topic_detail: str
    cefr_level: str = "A2"
    target_duration: str = "1 min"
    lesson_type: str = "random"
    speech_rate: float = 1.0


@app.post("/api/generate-lesson")
async def generate_lesson_endpoint(request: LessonRequest):
    try:
        chosen_type = request.lesson_type
        if chosen_type == "random":
            chosen_type = random.choice(["dialogue", "podcast"])

        app.state.lesson_counter += 1
        variation_step = app.state.lesson_counter

        result = await generate_smart_lesson(
            topic_detail=request.topic_detail,
            cefr_level=request.cefr_level,
            target_duration=request.target_duration,
            lesson_type=chosen_type,
            variation_step=variation_step
        )

        dynamic_rate = dynamic_speech_rate(
            base_rate=request.speech_rate,
            step=variation_step,
            spread=0.18,
            phase=0.25
        )

        return {
            "status": "success",
            "lesson_type": chosen_type,
            "level": request.cefr_level,
            "duration": request.target_duration,
            "speech_rate": dynamic_rate,
            "content": result["script"],
            "sentence_count": result.get("sentence_count", 0)
        }

    except Exception as e:
        print(f"❌ Lỗi tại endpoint generate-lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-lesson-audio")
async def generate_lesson_audio_endpoint(request: LessonRequest):
    try:
        chosen_type = request.lesson_type
        if chosen_type == "random":
            chosen_type = random.choice(["dialogue", "podcast"])

        app.state.lesson_counter += 1
        variation_step = app.state.lesson_counter

        result = await generate_smart_lesson(
            topic_detail=request.topic_detail,
            cefr_level=request.cefr_level,
            target_duration=request.target_duration,
            lesson_type=chosen_type,
            variation_step=variation_step
        )

        dynamic_rate = dynamic_speech_rate(
            base_rate=request.speech_rate,
            step=variation_step,
            spread=0.18,
            phase=0.25
        )

        script = result["script"]
        audio_bytes = await text_to_speech_multivoice(
            script_text=script,
            is_dialogue=(chosen_type == "dialogue"),
            speech_rate=dynamic_rate
        )

        return Response(content=audio_bytes, media_type="audio/mpeg")

    except Exception as e:
        print(f"❌ Lỗi audio endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-daily-audio")
async def generate_daily_audio_endpoint(
    custom_topic: str | None = Query(
        default=None,
        description="(Dùng khi Demo) Nhập chủ đề bất kỳ để ép tạo bài mới ngay lập tức. Để trống nếu chạy theo lịch 0h00."
    ),
    force_random_topic: bool = Query(
        default=False,
        description="(Dùng khi Demo) Đặt True nếu muốn random chủ đề khác trong tuần mà không cần tự gõ."
    )
):
    """
    - Bình thường 0h00 Cronjob gọi vào (không truyền tham số) -> Lấy đúng chủ đề của ngày hôm đó.
    - Khi Demo: Nhập custom_topic hoặc bật force_random_topic=True -> Xóa bài cũ, tạo bài mới chen ngang ngay lập tức!
    """
    try:
        info = await generate_daily_audio(
            custom_topic=custom_topic,
            force_random_topic=force_random_topic
        )
        return {
            "status": "success",
            "message": "Daily audio generated and overwritten successfully.",
            "data": info
        }
    except Exception as e:
        print(f"❌ Lỗi khi generate daily audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/version")
async def get_audio_version():
    """Endpoint nhẹ để ESP32 kiểm tra xem trên Server vừa có bản MP3 mới (do 0h00 hoặc do Demo) hay chưa"""
    storage_dir = Path(STORAGE_DIR)
    if not storage_dir.is_absolute():
        storage_dir = Path(__file__).resolve().parent / storage_dir

    version_file = storage_dir / "version.txt"
    if not version_file.exists():
        return {"version": "0"}

    return {"version": version_file.read_text(encoding="utf-8").strip()}


@app.get("/api/audio/current")
async def get_current_audio():
    """Endpoint để ESP32 tải file current.mp3 về thẻ nhớ SD"""
    storage_dir = Path(STORAGE_DIR)
    if not storage_dir.is_absolute():
        storage_dir = Path(__file__).resolve().parent / storage_dir

    file_path = storage_dir / "current.mp3"

    if not file_path.exists():
        print("⚠️ current.mp3 missing on request, generating now...")
        await generate_daily_audio()

    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename="current.mp3"
    )


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "IoT English Listening Device Backend is running."
    }