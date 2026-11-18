"""Small JSON-reporting command line interface; account login stays with callers."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from .browser import BrowserConfig, SolveOptions, solve
from .demo import serve
from .matching import MatchError, MatchOptions, match_images
from .synthetic import write_sample


def load_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    extra = set(data)-{"selectors","matching","execution"}
    if extra:
        raise ValueError("CONFIG_UNKNOWN_SECTION")
    config = BrowserConfig(**data["selectors"])
    options = SolveOptions(**data.get("execution",{}),matching=MatchOptions(**data.get("matching",{})))
    return config,options


def output(value,path=None):
    text = json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)
    if path:
        Path(path).write_text(text+"\n",encoding="utf-8")
    print(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local horizontal slider image matching and browser adapter")
    commands = parser.add_subparsers(dest="command",required=True)
    analyze = commands.add_parser("analyze",help="Analyze local image files without opening a browser")
    analyze.add_argument("--background",required=True)
    analyze.add_argument("--piece",required=True)
    analyze.add_argument("--piece-y",type=int)
    analyze.add_argument("--method",choices=["outline","template"],default="outline")
    analyze.add_argument("--display-width",type=float)
    analyze.add_argument("--output")
    sample = commands.add_parser("sample",help="Generate original synthetic example images")
    sample.add_argument("--output",default="samples")
    demo = commands.add_parser("demo",help="Serve the local synthetic demo site")
    demo.add_argument("--host",default="0.0.0.0")
    demo.add_argument("--port",type=int,default=18765)
    run = commands.add_parser("run",help="Run a configured adapter on an existing site's challenge")
    run.add_argument("--url",required=True)
    run.add_argument("--config",required=True)
    run.add_argument("--browser",choices=["chromium","msedge","chrome"],default="chromium")
    run.add_argument("--headless",action="store_true")
    run.add_argument("--prepare",action="store_true",help="Wait for Enter after the user brings up the challenge")
    run.add_argument("--keep-open",action="store_true",help="Wait for Enter before closing the browser")
    run.add_argument("--samples",help="Opt-in local image/metric recording directory")
    run.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            serve(args.host,args.port)
        elif args.command == "sample":
            write_sample(args.output)
            output({"status":"generated","directory":str(Path(args.output).resolve())})
        elif args.command == "analyze":
            result = match_images(Path(args.background).read_bytes(),Path(args.piece).read_bytes(),
                                  piece_y=args.piece_y,options=MatchOptions(method=args.method))
            data = result.to_dict()
            if args.display_width:
                data["distance_css"] = result.distance_css(args.display_width)
            output({"status":"matched",**data},args.output)
        else:
            if args.headless and (args.prepare or args.keep_open):
                raise ValueError("INTERACTIVE_FLAGS_REQUIRE_HEADED_BROWSER")
            config,options = load_config(args.config)
            if args.samples:
                options = replace(options,samples=args.samples)
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                output({"status":"error","reason":"BROWSER_EXTRA_REQUIRED","install":"pip install -e .[browser]"})
                return 2
            with sync_playwright() as playwright:
                launch = {"headless":args.headless}
                if args.browser != "chromium":
                    launch["channel"] = args.browser
                browser = playwright.chromium.launch(**launch)
                try:
                    page = browser.new_page()
                    page.goto(args.url,wait_until="domcontentloaded",timeout=45000)
                    if args.prepare:
                        input("让验证码显示在页面中后，按 Enter 开始识别：")
                    result = solve(page,config,options=options)
                    output(result.to_dict(),args.output)
                    if args.keep_open:
                        input("浏览器保留中，可手工操作；按 Enter 关闭：")
                    return 0 if result.passed else 2
                finally:
                    browser.close()
    except MatchError as error:
        output({"status":"manual","reason":error.code,"match":error.result.to_dict() if error.result else None},getattr(args,"output",None))
        return 2
    except (OSError,ValueError,TypeError,KeyError):
        output({"status":"error","reason":"INPUT_OR_CONFIG_INVALID"})
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception:
        # Avoid exposing URLs, form values or browser exception call logs.
        output({"status":"error","reason":"BROWSER_OPERATION_FAILED"})
        return 2
    return 0
