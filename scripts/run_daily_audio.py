import asyncio

from services.audio_service import generate_daily_audio


async def main():
    await generate_daily_audio()


if __name__ == "__main__":
    asyncio.run(main())