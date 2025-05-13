import os
from typing import Dict, Any, Optional
from asyncio import Lock
from tqdm import tqdm
from dataclasses import dataclass
import asyncio
import random
from loguru import logger


@dataclass
class ProgressTracker:
    total: int
    current: int = 0
    description: str = "Progress"
    _lock: Lock = Lock()
    bar_length: int = 30  # Progress bar length in characters

    def __post_init__(self):
        pass

    def _create_progress_bar(self, percentage: float) -> str:
        filled_length = int(self.bar_length * percentage / 100)
        bar = "█" * filled_length + "░" * (self.bar_length - filled_length)
        return bar

    async def increment(self, amount: int = 1, message: Optional[str] = None):
        async with self._lock:
            self.current += amount
            percentage = (self.current / self.total) * 100
            bar = self._create_progress_bar(percentage)

            # Add emoji based on progress
            emoji = "⏳"
            if percentage >= 100:
                emoji = "✅"
            elif percentage >= 50:
                emoji = "🔄"

            progress_msg = f"{emoji} [{self.description}] [{bar}] {self.current}/{self.total} ({percentage:.1f}%)"
            # if message:
            #     progress_msg += f"\n    ├─ {message}"
            logger.info(progress_msg)

    async def set_total(self, total: int):
        async with self._lock:
            self.total = total

    def __del__(self):
        pass  # Remove tqdm closing


async def create_progress_tracker(
    total: int, description: str = "Progress"
) -> ProgressTracker:
    return ProgressTracker(total=total, description=description)


async def process_item(tracker: ProgressTracker, item_id: int):
    delay = random.uniform(2, 5)
    await asyncio.sleep(delay)
    status = "completed" if random.random() > 0.2 else "pending"
    await tracker.increment(1, f"📝 Account {item_id} status: {status}")
