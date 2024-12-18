import queue
import threading
from logging import getLogger

from client import ApiClient

api = ApiClient("test")

logger = getLogger(__name__)


def empty_queue(queue: queue.Queue):
    while queue.qsize() > 0:
        yield queue.get_nowait()


def command_executor(command_queue: queue.Queue):
    try:
        while True:
            round = api.test_world()
            print(round)

            next_time = round["next"]
            timeout = round["turnEndsInSec"]

            try:
                commands = list(empty_queue(command_queue))
            except queue.Empty:
                # No command received in this round, skipping
                command = None

            logger

            if command == "exit":
                break
    finally:
        print("Command executor stopped")


command_queue = queue.Queue()
executor_thread = threading.Thread(
    target=command_executor,
    args=(command_queue,),
    daemon=True,
)
executor_thread.start()


try:
    while True:
        command_queue.put(input("Enter command: "))
except KeyboardInterrupt:
    command_queue.put("exit")
