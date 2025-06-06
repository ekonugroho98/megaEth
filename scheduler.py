import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from src.model.database import db_manager
import process
from src.utils.config import get_config
from src.utils.telegram_logger import send_telegram_message

async def send_notification(config, message):
    """Send notification if enabled in config"""
    if config.SCHEDULER.SEND_NOTIFICATIONS and config.SETTINGS.SEND_TELEGRAM_LOGS:
        await send_telegram_message(config, message)

async def send_test_notification(config):
    """Send a test notification to verify Telegram configuration"""
    test_message = (
        "🤖 Bot Notification Test\n\n"
        "✅ Telegram configuration is working!\n"
        "📅 Scheduler will run every {} minutes\n"
        "🔄 Next run will regenerate tasks and start farming"
    ).format(config.SCHEDULER.INTERVAL_MINUTES)
    
    await send_notification(config, test_message)

async def job():
    """Main job that regenerates tasks and starts farming"""
    config = get_config()
    retry_count = 0
    
    while retry_count < config.SCHEDULER.MAX_RETRIES:
        try:
            # Regenerate tasks for completed wallets
            logger.info("Starting task regeneration for completed wallets...")
            await send_notification(config, "🔄 Starting task regeneration for completed wallets...")
            await db_manager.regenerate_tasks_for_completed(auto_confirm=True)
            
            # Start farming
            logger.info("Starting farming process...")
            await send_notification(config, "🚀 Starting farming process...")
            await process.start(auto_run=True)
            
            # If we get here, everything succeeded
            logger.success("Scheduled job completed successfully")
            await send_notification(config, "✅ Scheduled job completed successfully")
            break
            
        except Exception as e:
            retry_count += 1
            error_msg = f"Error in scheduled job (attempt {retry_count}/{config.SCHEDULER.MAX_RETRIES}): {str(e)}"
            logger.error(error_msg)
            await send_notification(config, f"⚠️ {error_msg}")
            
            if retry_count < config.SCHEDULER.MAX_RETRIES:
                logger.info(f"Retrying in {config.SCHEDULER.RETRY_DELAY_SECONDS} seconds...")
                await asyncio.sleep(config.SCHEDULER.RETRY_DELAY_SECONDS)
            else:
                logger.error("Max retries reached. Giving up.")
                await send_notification(config, "❌ Max retries reached. Giving up.")

async def main():
    config = get_config()
    
    if not config.SCHEDULER.ENABLED:
        logger.info("Scheduler is disabled in config. Exiting...")
        return
        
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job, "interval", minutes=config.SCHEDULER.INTERVAL_MINUTES)
    scheduler.start()
    
    logger.info(f"Scheduler started with {config.SCHEDULER.INTERVAL_MINUTES} minute interval")
    
    # Send test notification
    await send_test_notification(config)
    
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
        await send_notification(config, "🛑 Scheduler stopped by user")

if __name__ == "__main__":
    asyncio.run(main())
