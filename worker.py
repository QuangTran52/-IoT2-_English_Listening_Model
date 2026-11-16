import asyncio
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.audio_service import generate_daily_audio


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        generate_daily_audio,
        trigger=CronTrigger(
            hour=0,
            minute=0,
            second=0,
            timezone=ZoneInfo("Asia/Ho_Chi_Minh")
        )
    )
    scheduler.start()
    print("✅ Worker started; daily audio will generate at 00:00 Asia/Ho_Chi_Minh")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())