"""
https://github.com/yoyonel/asyncio_producer_consumer
"""
import asyncio
from typing import List


async def do_shutdown(loop) -> List[Exception]:
    """
    https://pythonexample.com/code/asyncio-cancel-all-tasks/

    :param loop:
    :return:
    """
    tasks = [
        task
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    ]
    list(map(lambda task: task.cancel(), tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    return results
