import asyncio
import json

import websockets

from store.connect import async_db


# Query function
async def fetch_data(conn, name, start, batch_size=10):
    query = """
    SELECT turn, data
    FROM replays
    WHERE name = $1
    ORDER BY turn ASC
    OFFSET $2
    LIMIT $3;
    """
    return await conn.fetch(query, name, start, batch_size)


# WebSocket handler
async def handle_client(websocket, path):
    print("New client connected")
    conn = await async_db()
    name = None
    start = 0
    batch_size = 10
    streaming = False
    rate = 1

    async def stream_data():
        nonlocal name, start, streaming
        while True:
            if streaming and name is not None:
                # Fetch a batch of data from the database
                rows = await fetch_data(conn, name, start, batch_size)
                if rows:
                    results = [
                        {"turn": row["turn"], "data": row["data"]} for row in rows
                    ]
                    await websocket.send(json.dumps({"data": results}))
                    start += batch_size
                else:
                    # No more data available; pause streaming
                    streaming = False
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
                start = data.get("start", 0)
                streaming = True  # Resume streaming with new parameters
                await websocket.send(json.dumps({"status": "streaming updated"}))
            else:
                await websocket.send(json.dumps({"error": "Invalid command"}))

    except websockets.ConnectionClosed:
        print("Client disconnected")
    finally:
        await conn.close()


# Start WebSocket server
async def main():
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("WebSocket server is running on ws://localhost:8765")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
