# Slider Captcha Kit

可复用的**横向滑块拼图识别与自动拖动工具**。Python 3.11+，MIT 许可证，图片在本地分析，不需要 API Key。

把图片识别、拖动轨迹和网站接入分开。换网站时配置选择器；已有 Playwright 爬虫只需在验证码出现时调用一次，原来的登录、定时调度和采集代码继续由你的程序负责。

## 包含什么

- **离线识别**：输入背景图和透明拼图块，输出横向位置、最高分和次高分。
- **两种算法**：白色轮廓匹配 `outline`；带透明蒙版、可处理亮度变化的纹理匹配 `template`。
- **Playwright 同步适配器**：配置图片、按钮、刷新、失败和成功状态选择器；扫描主页面和 iframe。
- **图片读取**：Base64、同源或允许 Canvas 读取的普通 `<img>`、Canvas。
- **拖动**：原图像素换算为 CSS 距离；缓动、轻微抖动与有界过冲；鼠标按下前再次检查图片。
- **有界重试**：最多三次；低分、歧义、图片变化或服务器未确认时返回人工处理状态。
- **可选样本**：只在显式指定目录后保存图片与白名单数值元数据。
- **本地演示、测试和 CI**：使用本项目生成的合成图片，示例站独立校验拖动结果。

适用范围是“背景图 + 透明拼图块”的横向拼图。它依靠实际拖动完成网站自己的校验，不能保证任意网站、任意验证码通用。点选、旋转、重排、短信、UKey 和独立行为验证不在本版本范围内；跨域图片如果不能被 Canvas 读取，交由调用方提供已获授权的图片字节。纹理不相似或白色轮廓不存在时，需要换算法或另写 matcher。

## 三分钟运行本地演示

Windows PowerShell，在解压后的项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[browser]"
python -m playwright install chromium
slider-kit demo
```

如果系统限制激活脚本，可直接使用 `.\.venv\Scripts\python.exe` 和 `.\.venv\Scripts\slider-kit.exe`。

打开 <http://127.0.0.1:18765>，可以先手动拖动。演示服务默认绑定 `0.0.0.0:18765`，局域网可通过运行机 IP 预览，无需登录。

另开一个终端，激活同一个虚拟环境，运行：

```powershell
slider-kit run --url http://127.0.0.1:18765 --config configs/demo.json
```

返回 `"status": "solved"`、`"passed": true` 表示本地服务已确认结果。也可以使用已经安装的 Edge：

```powershell
slider-kit run --url http://127.0.0.1:18765 --config configs/demo.json --browser msedge
```

Linux/macOS 的虚拟环境激活命令为 `source .venv/bin/activate`，其他命令相同。纯图片识别只需 `pip install -e .`，无需安装 Playwright。

## 接入已有爬虫

```python
from slider_captcha_kit import BrowserConfig, SolveOptions, solve

config = BrowserConfig(
    background=".puzzle-background img",
    piece=".puzzle-piece img",
    piece_container=".puzzle-piece",
    handle=".slider-handle",
    panel=".puzzle-background",
    refresh=".puzzle-refresh",
    failure=".puzzle-error:visible",
    success=".verification-success:visible",
)

# 使用你已经打开、已经提交登录表单的 Playwright page。
result = solve(page, config, options=SolveOptions(max_attempts=3))
if result.passed:
    continue_your_collection()
else:
    notify_operator(result.reason)  # 此处由你的程序等待人工；solve 不关闭浏览器。
```

`continue_your_collection` 和 `notify_operator` 表示你已有的业务函数。可执行的完整浏览器示例见 [examples/playwright_integration.py](examples/playwright_integration.py)。

成功判定必须配置为**校验通过后才出现的状态**，也可以传 `success=lambda page: ...`。仅仅看到滑块消失不会被判为成功。网站要求后续短信、证书认证时，把“已进入下一认证步骤”的真实可见状态作为当前滑块阶段的成功条件，再由原登录代码继续执行。

网站配置示例见 [configs/site.example.json](configs/site.example.json)，逐项适配方法见 [网站适配指南](docs/adapting.md)。此模板需要按目标页面修改，不能直接用于任意网站。

## 只分析图片，自己负责浏览器操作

```python
from pathlib import Path
from slider_captcha_kit import MatchOptions, match_images

match = match_images(
    Path("background.png").read_bytes(),
    Path("piece.png").read_bytes(),
    options=MatchOptions(method="outline"),
)
print(match.to_dict())
distance = match.distance_css(display_width=330, piece_start_css=0)
```

`offset_x` 是拼图图片左边缘在背景原图中的目标坐标，不一定等于鼠标拖动距离。

```text
CSS 拖动距离 = offset_x × 背景显示宽度 ÷ 背景原图宽度 − 拼图当前 CSS 横向偏移
```

如果拼图是裁剪后的小图，需指定 `piece_y`（原图像素中的纵向坐标）。浏览器适配器可从 DOM 位置推算，遇到 padding、transform 或额外图片边距时应按实际布局配置。

## 命令行图片工具

```powershell
slider-kit sample --output samples
slider-kit analyze --background samples/outline_background.png --piece samples/outline_piece.png --display-width 330
slider-kit analyze --background samples/template_background.png --piece samples/template_piece.png --method template --piece-y 64
```

分析成功返回 JSON。退出码：`0` 成功，`2` 需要人工或输入/配置错误，`130` 用户中止。JSON 的 `reason` 提供具体结果；匹配分数是算法指标，不是自动通过的概率。

## 重试、样本与关闭开关

```python
options = SolveOptions(
    max_attempts=3,
    detection_timeout=5,
    result_timeout=8,
    samples="./private/samples",  # 默认 None：不保存图片。
)
result = solve(page, config, options=options)

# 单次任务回退人工，不发生鼠标操作。
result = solve(page, config, options=SolveOptions(enabled=False))
```

样本含图片和 `attempts.jsonl`，不保存 URL、DOM、Cookie、账号、密码或任意异常文本。实际站点样本属于你的运行数据，不应混进源码或提交公开仓库。CLI 的 `--samples ./private/samples` 开启相同记录。

CLI 的 `--prepare` 会等你手工打开验证码后再识别；`--keep-open` 会保留浏览器直到按回车。无人值守任务建议直接调用库，由原调度系统处理返回结果。

## 扩展与验证

自定义图片算法通过 `matcher=` 注入；可执行的纹理 matcher 示例见 [examples/custom_matcher.py](examples/custom_matcher.py)。本版本没有 AI 服务、模型调用、远程识别接口或密钥配置。

```powershell
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m pytest -q
python -m build
```

本机若只装了 Edge，可设置 `$env:SLIDER_KIT_TEST_BROWSER='msedge'` 后运行测试。没有浏览器时集成测试会明确 skip，不能把 skip 当作真实浏览器验证通过。自动化覆盖像素匹配、歧义、缩放、轨迹边界、图片刷新、iframe、普通图片/Canvas、服务端结果确认和本地日志字段。

[验证记录](docs/verification.md)说明当前压缩包实际运行过的检查。仅在自有站点或获授权的账号与环境中使用；保持目标站点允许的访问频率。

## 目录

```text
src/slider_captcha_kit/  图片算法、浏览器适配器、CLI、本地演示
configs/                 可修改的网站选择器配置
examples/                Python 接入示例和合成图片
tests/                   单元与真实浏览器集成测试
docs/                    适配方法、验证记录
scripts/                 可重复生成源码压缩包
.github/workflows/       GitHub 测试和构建流程
```

开源许可：[MIT](LICENSE)。第三方依赖说明：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。此交付为本地源码包，尚未推送公开 GitHub 或发布到 PyPI。
