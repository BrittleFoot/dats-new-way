import asyncio
from itertools import cycle
import json
from pprint import pprint
from random import shuffle
from typing import NamedTuple

import websockets # type: ignore

from store.connect import async_db
from urllib.parse import parse_qs, urlparse


client_emoji = ['🐶', '🐟', '🐱', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁']
shuffle(client_emoji)
client_avatars = cycle(client_emoji)



MIN_BATCH_SIZE = 1

SELECT_REPLAY_QUERY = """
    SELECT id, turn, data
    FROM replays
    WHERE name = %(name)s AND turn >= %(turn)s
    ORDER BY turn ASC
    LIMIT %(batch_size)s
"""


def replay2dict(record):
    id, turn, data = record
    return dict(id=id, turn=turn, data=data)


def summary2dict(record):
    name, turns = record
    return dict(name=name, turns=turns)



def rsp_replay(data):
    return {
        "type": "replay",
        "data": data,
    }


def rsp_summary(replays):
    return {
        "type": "summary",
        "replays": list(map(summary2dict, replays)),
    }


async def db_summary(conn):
    async with conn.cursor() as cur:
        await cur.execute("SELECT name, MAX(turn) FROM replays GROUP BY name")
        return rsp_summary(await cur.fetchall())

# WebSocket handler
async def handle_client(websocket, path):
    avatar = next(client_avatars)

    print(f"\n{avatar} 🔥 New client connected on", path)
    # Parse query parameters from path
    query_params = parse_qs(urlparse(path).query)

    # Extract specific parameters if available
    name = query_params.get('name', [None])[0]
    turn = int(query_params.get('turn', [0])[0])
    nowelcome = query_params.get('nowelcome', [None])[0]
    should_welcome = not nowelcome

    batch_size = 5
    stream_modifier = 1

    streaming = name is not None
    rate = 1

    async with await async_db() as conn, conn.cursor() as cur:

        async def stream_data():
            nonlocal name, turn, streaming, stream_modifier
            while True:
                # Stream ended, or paused
                if not streaming:
                    await asyncio.sleep(rate)
                    continue

                size = batch_size * stream_modifier
                await cur.execute(SELECT_REPLAY_QUERY, dict(name=name, turn=turn, batch_size=size))
                batch = list(map(replay2dict, await cur.fetchall()))

                if not batch:
                    streaming = False
                    print(f"\n{avatar} 🏁 Streaming completed")
                    break

                print(avatar, end="", flush=True)

                await websocket.send(json.dumps(rsp_replay(batch)))
                turn = batch[-1]["turn"] + 1

                await asyncio.sleep(rate)  # Control streaming rate

        try:
            # Start the streaming loop
            stream_task = asyncio.create_task(stream_data())

            if should_welcome:
                summary = await db_summary(conn)
                await websocket.send(json.dumps(summary))

            while True:
                # Wait for control messages
                message = await websocket.recv()
                data = json.loads(message)

                # Validate incoming data
                if "name" in data:
                    name = data["name"]
                    turn = data.get("turn", 0)
                    streaming = True  # Resume streaming with new parameters
                    await websocket.send(json.dumps({"status": "streaming updated"}))
                else:
                    await websocket.send(json.dumps({"error": "Invalid command"}))

        except websockets.ConnectionClosed:
            print(f"\n{avatar} 😵 Client disconnected")

        stream_task.cancel()
        await stream_task


# Start WebSocket server
async def main():
    async with websockets.serve(handle_client, "localhost", 8765) as server:
        print("🏃 WebSocket server is running on ws://localhost:8765")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
