#! src="https://pygame-web.github.io/archives/0.9/pythons.js" data-os="vtx,fs,gui" data-python="python3.12" data-lines="48" data-console="18"
import asyncio

from bruce_game import run_browser

print("Browser runtime booted.")
print("Importing Bruce's Treasure...")
print("Starting browser game loop...")

asyncio.run(run_browser())
