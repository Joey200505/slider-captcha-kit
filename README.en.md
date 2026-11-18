# Slider Captcha Kit

[![Tests](https://github.com/Joey200505/slider-captcha-kit/actions/workflows/tests.yml/badge.svg)](https://github.com/Joey200505/slider-captcha-kit/actions/workflows/tests.yml)

[中文说明](README.md) · [Issues](https://github.com/Joey200505/slider-captcha-kit/issues) · [MIT license](LICENSE)

A local image matcher and configurable synchronous Playwright adapter for horizontal slider puzzles. Requires Python 3.11+. Image processing runs locally with NumPy and Pillow; no API key is needed.

Features include outline and masked template matching, CSS coordinate conversion, iframe and Canvas support, bounded retries, explicit success confirmation, and optional local sample recording. The demo uses original synthetic images and verifies drag results on its own HTTP server.

## Install and try the demo

```sh
git clone https://github.com/Joey200505/slider-captcha-kit.git
cd slider-captcha-kit
python -m venv .venv
```

Activate the environment with `.\.venv\Scripts\Activate.ps1` on Windows PowerShell or `source .venv/bin/activate` on Linux/macOS, then run:

```sh
python -m pip install -e '.[browser]'
python -m playwright install chromium
slider-kit demo
```

Open [the local demo](http://127.0.0.1:18765). It needs no login and binds to `0.0.0.0:18765`, so it is also reachable through your machine's LAN IP. In a second terminal using the same environment:

```sh
slider-kit run --url http://127.0.0.1:18765 --config configs/demo.json
```

`"status": "solved"` and `"passed": true` mean the demo server confirmed the result. Use `--browser msedge` to launch an installed Microsoft Edge instead.

## Use in an existing Playwright flow

```python
from slider_captcha_kit import BrowserConfig, SolveOptions, solve

config = BrowserConfig(
    background="#background", piece="#piece", handle="#handle",
    panel="#panel", refresh="#refresh", failure="#failure", success="#verified",
)
result = solve(page, config, options=SolveOptions(max_attempts=3))
print(result.to_dict())
```

Use your existing `page` after bringing up the challenge; configure selectors for your own site. The success selector must identify an actual confirmed state. The caller handles login, scheduling, subsequent authentication, and any manual fallback. See the [complete example](examples/playwright_integration.py) and [adaptation guide (Chinese)](docs/adapting.md).

## Offline matching

For image matching alone, install with `python -m pip install -e .`.

```sh
slider-kit sample --output samples
slider-kit analyze --background samples/outline_background.png --piece samples/outline_piece.png --display-width 330
```

The matcher returns the target position in original image pixels. Drag distance also depends on display scaling and the piece's initial position. See the [API examples](README.md) for details.

## Development

```sh
python -m pip install -e '.[dev]'
python -m playwright install chromium
python -m pytest -q
python scripts/check_docs.py
python -m build
```

Tests exercise synthetic images and a local browser demo. See the [verification record](docs/verification.md), [contribution guide](CONTRIBUTING.md), and [dependency notices](THIRD_PARTY_NOTICES.md).

Use only on sites and environments you own or are authorized to test, at permitted request rates. This package supports horizontal background-and-transparent-piece puzzles; other challenge types need a different integration. Samples are opt-in and private runtime data should stay out of public repositories. Saved images have embedded metadata removed; logs accept only selected metrics. Install from source using the instructions above.
