# Browser Run

The game now uses a shared module in `bruce_game.py` with two launchers:

- `main.py` for desktop
- `browser_main.py` for browser packaging

## One Command Build

Run:

```bash
./build_pages.sh
```

That creates:

```text
docs/index.html
docs/browser_app.apk
docs/browser_app.tar.gz
docs/favicon.png
docs/favicon.ico
```

`build_pages.sh` also pins `pygbag` to the archived web runtime at `https://pygame-web.github.io/archives/0.9/` with Python `3.12`, because the locally installed `pygbag 0.9.4` package currently defaults to a `cdn/0.9.4` path that is not booting reliably.

The build uses a local `pygbag-local.tmpl` page that explicitly asks for `python3.12`, loads the packaged `browser_app.apk`, and shows a small on-page loader log while the runtime downloads resources.

Open the site root after starting your local server:

```text
http://127.0.0.1:8000/
```

Do not open `/browser_app.html`; that was only used by the older broken embed build.

You can test it locally with:

```bash
python -m http.server -d docs 8000
```

## Manual Build

Run:

```bash
./prepare_browser_build.sh
python -m pygbag --build --disable-sound-format-error --version 0.9.2 --PYBUILD 3.12 --cdn https://pygame-web.github.io/archives/0.9/ --template pygbag-local.tmpl build/browser_app
```

Then serve either `docs/` or copy `build/browser_app/build/web/` somewhere static.

## Notes

- The browser build runs in a windowed mode instead of fullscreen.
- `pygbag` expects the packaged app folder to contain a `main.py`, which is why the prep script copies `browser_main.py` into `build/browser_app/main.py`.
- `browser_main.py` starts with a browser-only shebang comment that tells `pygbag` to request `python3.12` and allocates a larger visible console during startup.
- This repo includes `pygbag-local.tmpl` to avoid the current `pygbag 0.9.4` CDN lookup for `default.tmpl`, which is returning 404.
- The build intentionally overrides `pygbag`'s default `cdn/0.9.4` bootstrap and uses the archived `0.9` runtime instead, because the default path was leaving the page stuck on the "Downloading" screen.
- `docs/index.html` is the actual app page. It loads `docs/browser_app.apk` rather than relying on the fragile `--html` single-file embed mode.
- Browser audio support is stricter than desktop. OGG files are the safest option, so WAV/MP3 effects may need conversion if you want full web audio coverage.
