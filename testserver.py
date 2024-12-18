"""
Test server

This is a simple test server that simulates the behavior of the DAD server.

It generates a some world set and sends it to the client.

Also, it simulates network latency by waiting 0.3 seconds before sending a response.

"""

import math
from itertools import cycle
from os import environ
from time import sleep, time

import numpy as np
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()


load_dotenv()

KEY = environ["DAD_TOKEN"]


app = FastAPI()


def mandelbrot_step(xmin, xmax, ymin, ymax, width, height, max_iter):
    """
    Generator that yields points to draw for each iteration step in the Mandelbrot set.
    The output is serialized as JSON containing points where the value does not escape.
    """
    x = np.linspace(xmin, xmax, width)
    y = np.linspace(ymin, ymax, height)

    # Create complex plane
    c = x[np.newaxis, :] + 1j * y[:, np.newaxis]
    z = np.zeros_like(c)
    mask = np.ones_like(c, dtype=bool)  # Points that haven't escaped yet

    for n in range(max_iter):
        z[mask] = z[mask] ** 2 + c[mask]
        escaped = np.abs(z) > 2  # Points that escape this iteration
        new_points = np.argwhere(mask & escaped)

        # Serialize points that escaped in this step
        result = [{"x": int(pt[1]), "y": int(pt[0])} for pt in new_points]
        yield result

        # Update mask to mark escaped points
        mask &= ~escaped


# Parameters
xmin, xmax, ymin, ymax = -2.0, 1.0, -1.5, 1.5
width, height = 100, 100  # Lower resolution for faster demo
max_iter = 50

# Generate Mandelbrot steps
generator = cycle(
    enumerate(mandelbrot_step(xmin, xmax, ymin, ymax, width, height, max_iter))
)


@app.get("/")
def read_root(request: Request):
    if request.headers.get("X-Auth-Token") != KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    time_sec = time()
    next_time = math.ceil(time_sec)

    if next_time - time_sec < 0.3:
        next_time += 1

    sleep(0.3)

    step, map = next(generator)

    return {
        "next": next_time,
        "turn": step,
        "turnEndsInSec": next_time - time(),
        "map": map,
    }


@app.get("submit")
def submit_command(commands: list[str], request: Request):
    if request.headers.get("X-Auth-Token") != KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {"accepted": commands}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
