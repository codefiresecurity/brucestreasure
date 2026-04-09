# Browser Run

The game now uses a shared module in `bruce_game.py` with two launchers:

- `main.py` for desktop
- `browser_main.py` for browser packaging

## Prepare A Browser Build

Run:

```bash
./prepare_browser_build.sh
python -m pygbag --disable-sound-format-error build/browser_app
```

Then open `http://localhost:8000`.

## Notes

- The browser build runs in a windowed mode instead of fullscreen.
- `pygbag` expects the packaged app folder to contain a `main.py`, which is why the prep script copies `browser_main.py` into `build/browser_app/main.py`.
- Browser audio support is stricter than desktop. OGG files are the safest option, so WAV/MP3 effects may need conversion if you want full web audio coverage.
