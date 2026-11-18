from dataclasses import replace
import json
import os
import threading

import pytest

from slider_captcha_kit import BrowserConfig, SolveOptions, solve
from slider_captcha_kit.cli import load_config
from slider_captcha_kit.demo import DemoServer

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def server():
    server = DemoServer(("127.0.0.1",0))
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown();server.server_close();thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        launch = {"headless":True}
        if os.getenv("SLIDER_KIT_TEST_BROWSER"):
            launch["channel"] = os.environ["SLIDER_KIT_TEST_BROWSER"]
        try:
            browser = p.chromium.launch(**launch)
        except playwright.Error as error:
            if "Executable doesn't exist" in str(error):
                pytest.skip("Install the browser with python -m playwright install chromium")
            raise
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page()
    yield page
    page.close()


def config():
    return BrowserConfig(background="#background",piece="#piece",handle="#handle",panel="#panel",
                         refresh="#refresh",failure="#failure",success="#verified")


@pytest.mark.parametrize("query,frame",[("",None),("?image=canvas",None),("?image=remote",None),
                                      ("?frame=1",None),("?frame=1","#puzzle-frame")])
def test_real_mouse_and_server_validation(page,server,query,frame,tmp_path):
    page.goto(server+query)
    result = solve(page,replace(config(),frame=frame),options=SolveOptions(samples=str(tmp_path)))
    assert result.status == "solved"
    assert len(result.attempts) == 1
    assert result.attempts[0].match["score"] == 1.0
    assert json.loads((tmp_path/"attempts.jsonl").read_text().splitlines()[-1])["outcome"] == "solved"


def test_panel_disappearing_alone_is_not_success(page,server):
    page.goto(server+"?hide_only=1")
    result = solve(page,config(),options=SolveOptions(max_attempts=1,result_timeout=.6))
    assert not result.passed
    assert result.reason == "PLATFORM_NOT_CONFIRMED"


def test_refresh_dispatched_by_mouse_hover_is_rechecked(page,server):
    page.goto(server)
    page.locator("#background").wait_for(state="visible")
    page.locator("#handle").evaluate("""el => el.addEventListener('pointerenter',()=>{
        document.querySelector('#background').src=document.querySelector('#piece').src;
    },{once:true})""")
    result = solve(page,config(),options=SolveOptions(max_attempts=2,result_timeout=1))
    assert result.passed
    assert result.attempts[0].reason == "IMAGE_CHANGED"
    assert len(result.attempts) == 2


def test_custom_success_callback_and_disabled_mode(page,server):
    page.goto(server)
    cfg = replace(config(),success=None)
    with pytest.raises(ValueError,match="SUCCESS_SELECTOR_OR_CALLBACK_REQUIRED"):
        solve(page,cfg)
    assert solve(page,cfg,options=SolveOptions(enabled=False)).status == "disabled"
    result = solve(page,cfg,success=lambda p:p.locator("#verified").is_visible())
    assert result.passed


def test_scaled_images_and_nonzero_piece_start(page,server):
    page.goto(server)
    page.locator("#background").wait_for(state="visible")
    page.wait_for_function("document.querySelector('#background').naturalWidth===360")
    page.locator("#challenge").evaluate("el=>{el.style.width='270px';el.style.maxWidth='none'}")
    # Move the visual piece's starting origin by 10 CSS pixels. The demo's
    # pointer handler uses dx from zero, so account for that initial position.
    page.locator("#piece").evaluate("el=>el.style.left='10px'")
    cfg=config()
    seen=[]
    def matching(bg,part,**kwargs):
        from slider_captcha_kit import match_images
        result=match_images(bg,part,**kwargs)
        seen.append(result)
        return result
    # The demo resets pointer dx to zero, so the adapter must not report success
    # for this deliberately inconsistent setup even though the distance is right.
    result=solve(page,cfg,matcher=matching,options=SolveOptions(max_attempts=1,result_timeout=.6))
    assert not result.passed
    assert result.attempts[0].distance_css==pytest.approx(seen[0].offset_x*270/360-10)
    # A fresh scaled challenge must pass with its actual initial geometry.
    page.goto(server)
    page.locator("#challenge").evaluate("el=>{el.style.width='270px';el.style.maxWidth='none'}")
    assert solve(page,cfg).passed


def test_configuration_rejects_unbounded_attempts():
    with pytest.raises(ValueError):
        SolveOptions(max_attempts=10)
