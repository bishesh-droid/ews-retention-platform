#!/usr/bin/env python3
"""Entry point for the scheduler service."""
import asyncio
import sys

sys.path.insert(0, '/app')

from backend.services.infrastructure.scheduler import SchedulerService


async def main():
    scheduler = SchedulerService()
    await scheduler.start()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
