# 0.1.0 验证记录

核验日期：2026-11-18。范围为公开仓库中的图片接口、Playwright 适配器、本地演示、样本记录和发行包。

## 本地验证

**53 项测试通过，无 skip**：图片、CLI、样本与真实浏览器测试 40 项，源码打包测试 13 项。

- Windows，Python 3.11.9。
- NumPy 2.4.6、Pillow 12.3.0、Playwright 1.65.2、pytest 9.2.0、build 1.6.1。
- 真实浏览器使用本机 Microsoft Edge 的 headless 模式，仅访问本项目合成图片演示站。
- 演示服务绑定 `0.0.0.0:18765`，通过本机局域网 IP 调用 CLI，服务端确认 `status=solved`、`passed=true`。

```powershell
$env:SLIDER_KIT_TEST_BROWSER='msedge'
python -m pytest -q tests/test_browser.py tests/test_cli.py tests/test_matching.py tests/test_samples.py
python -m pytest -q tests/test_package.py
python scripts/check_docs.py
python -m build
python scripts/package.py --output dist/slider-captcha-kit-v0.1.0.zip
git diff --check
```

wheel 和源码发行包构建完成后，在独立虚拟环境安装 wheel 并用 `python -I` 检查包导入、演示 HTML 资源和安装后的 CLI；依赖从公开包源安装。源码 ZIP 包含逐文件 SHA-256 清单，并生成整个 ZIP 的 SHA-256 文件。

## 覆盖范围

- 白色轮廓、透明蒙版纹理、低分、歧义、裁剪拼图纵向位置、图像尺寸与搜索计算量限制。
- 有界轨迹、正确终点、过冲边界、CSS 缩放与初始横向偏移。
- 主页面、自动扫描 iframe、显式 iframe、Base64、普通同源图片及 Canvas。
- 真实鼠标事件拖动与本地 HTTP 服务确认；滑块单独消失不能判为成功。
- 鼠标移入导致图片刷新时，在按下前发现并重试。
- 可选样本、日志字段白名单、写盘失败处理、JPEG 转 PNG、PNG 文本和 EXIF 清除，同时保持 RGBA 像素。
- 源码 ZIP 仅收录逐项声明的文件，排除未声明的 `.env`、本地 JSON 配置和 Python 文件；拒绝无效路径、重复或缺失声明，校验哈希和可重复构建。

本轮未使用业务站点账号、数据库或真实验证码图片。图片夹具与合成函数一致，不含文本或 EXIF；公开文件未发现密钥和业务连接信息。

## 持续集成与代码审查

[GitHub Actions](https://github.com/Joey200505/slider-captcha-kit/actions/workflows/tests.yml) 在 push 和 PR 中执行 Python 3.11/3.13 + Ubuntu Chromium 测试、文档链接检查、发行包构建和源码 ZIP 打包；实际运行结果以该页面记录为准。

独立代码审查覆盖源码、测试、打包、配置和文档。发现的 PNG 元数据保留与递归打包私有文件风险已修复并补充回归测试；发布准备通过 PR 复核后合并。

其他网站、异步 Playwright、Selenium、CSS background-image、封闭 Shadow DOM 和其他验证码形态未在本轮验证，适配限制见 [适配指南](adapting.md)。
