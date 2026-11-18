"""Keep your existing login flow and call the adapter only when needed."""
import argparse

from playwright.sync_api import sync_playwright
from slider_captcha_kit import solve
from slider_captcha_kit.cli import load_config

parser = argparse.ArgumentParser()
parser.add_argument("--url",default="http://127.0.0.1:18765")
parser.add_argument("--config",default="configs/demo.json")
args = parser.parse_args()
config,options = load_config(args.config)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(args.url)
    # For another site, run your own authorized login steps here. Credentials
    # belong in your application's secret store, not in this reusable library.
    result = solve(page,config,options=options)
    print(result.to_dict())
    # The library never closes the page or completes CA/SMS steps for you.
    if not result.passed:
        print("请在浏览器手工完成验证，再回到终端。")
    input("按 Enter 关闭演示浏览器：")
    browser.close()
