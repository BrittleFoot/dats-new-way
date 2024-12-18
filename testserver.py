import math
from os import environ
from time import sleep, time

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()


load_dotenv()

KEY = environ["DAD_TOKEN"]


app = FastAPI()


@app.get("/")
def read_root(request: Request):
    if request.headers.get("X-Auth-Token") != KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    time_sec = time()
    next_time = math.ceil(time_sec)

    if next_time - time_sec < 0.3:
        next_time += 1

    sleep(0.3)

    return {"next": next_time, "turnEndsInSec": next_time - time()}


@app.get("submit")
def submit_command(commands: list[str], request: Request):
    if request.headers.get("X-Auth-Token") != KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {"accepted": commands}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
