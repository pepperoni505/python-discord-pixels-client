import template_manager
import os
import json
import asyncio
from PIL import Image
from dotenv import load_dotenv
from pixels.client import Client
from pixels.autodraw import AutoDrawer

load_dotenv(".env")
token = os.getenv("TOKEN")

client = Client(token)

dirname = os.path.dirname(__file__)

fbw_tail = os.path.join(dirname, 'images/FBW-Tail.png')
obamium = os.path.join(dirname, 'images/obamium')

with open(os.path.join(obamium, 'canvas.json')) as f:
    canvas_json = json.load(f)

async def main():
    auto_draw = AutoDrawer(client, obamium, canvas_json['left'], canvas_json['top'], is_animated=True)
    await auto_draw.draw(is_guarded=True)

asyncio.run(main())