import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.model.database import db_manager
import process

async def job():
    await db_manager.regenerate_tasks_for_completed(auto_confirm=True)
    await process.start(auto_run=True)

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job, "interval", hours=24)
    scheduler.start()
    print("Scheduler started. Press Ctrl+C to exit.")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    asyncio.run(main())
