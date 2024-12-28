import asyncio
from itertools import cycle
import json
from random import shuffle

import websockets # type: ignore

from store.connect import async_db
from urllib.parse import parse_qs, urlparse


client_emoji = ['🐶', '🐟', '🐱', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁']
shuffle(client_emoji)
client_avatars = cycle(client_emoji)


# Query function
async def fetch_data(conn, name, turn, batch_size=10):
    query = """
    SELECT turn, data
    FROM replays
    WHERE name = $1 AND turn >= $2 AND turn < $2 + $3
    ORDER BY turn ASC
    """
    return await conn.fetch(query, name, turn, batch_size)


# WebSocket handler
async def handle_client(websocket, path):
    avatar = next(client_avatars)

    print(f"\n{avatar} 🔥 New client connected on", path)
    # Parse query parameters from path
    query_params = parse_qs(urlparse(path).query)

    # Extract specific parameters if available
    name = query_params.get('name', [None])[0]
    turn = int(query_params.get('turn', [0])[0])

    batch_size = 10
    streaming = True
    rate = 1

    conn = await async_db()


    async def stream_data():
        nonlocal name, turn, streaming
        while True:
            if not streaming:
                await asyncio.sleep(rate)
                continue

            rows = await fetch_data(conn, name, turn, batch_size)
            if not rows:
                streaming = False
                break

            print(avatar, end="", flush=True)

            results = [
                {"turn": row["turn"], "data": row["data"]} for row in rows
            ]
            await websocket.send(json.dumps({"data": results}))
            turn += batch_size

            await asyncio.sleep(rate)  # Control streaming rate

    try:
        # Start the streaming loop
        asyncio.create_task(stream_data())

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
    finally:
        await conn.close()


# Start WebSocket server
async def main():
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("WebSocket server is running on ws://localhost:8765")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
