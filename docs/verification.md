# 0.1.0 验证记录

核验日期：2026-11-18。范围为本独立项目的源码、图片接口、Playwright 适配器、本地演示与安装产物。

结果：**39 项测试通过，无 skip**。wheel 和源码发行包构建通过，独立虚拟环境导入和演示资源检查通过。

## 实际运行环境

- Windows，Python 3.13.5。
- NumPy 2.4.4，Pillow 11.1.0，Playwright 1.58.0，pytest 8.3.4。
- 真实浏览器测试使用本机 Microsoft Edge 的 headless 模式。
- 所有浏览器自动化针对本项目本地演示站；没有在本批重新访问外部业务站点。

## 验证命令

```powershell
$env:SLIDER_KIT_TEST_BROWSER='msedge'
python -m pytest -q
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir ../slider-kit-build
python scripts/check_docs.py
git diff --check
```

另在独立虚拟环境安装构建出的 wheel，使用 `python -I` 检查包导入和随包演示 HTML 资源，并实际运行安装后的 `slider-kit run`，本地服务返回 `solved`、`passed=true`；该环境通过 `--system-site-packages` 复用已装依赖，没有假称完成隔离的网络依赖安装。

## 验证边界

- 覆盖白色轮廓、透明蒙版纹理、低分、歧义、裁剪拼图纵向位置、图片大小与搜索计算量限制。
- 覆盖有界轨迹、正确终点、过冲边界、CSS 缩放与初始横向偏移。
- 覆盖主页面、自动扫描 iframe、显式 iframe、Base64、普通同源图片及 Canvas。
- 使用真实鼠标事件拖动，由本地 HTTP 服务校验结果；滑块单独消失但未获确认时不能成功。
- 验证鼠标移入后同步刷新图片会在按下前被发现，换图后才重试；图片尚未加载时不会误消耗一次识别尝试。
- 验证本地样本可选、日志字段白名单、写盘失败不阻断和 JPEG 样本规范化为 PNG。
- 使用原运行机保留的五组成功样本做离线回归：原偏移 182、108、225、244、225；独立包输出全部一致。真实图片未复制进项目或压缩包。

GitHub CI 已提供 Python 3.11/3.13 + Ubuntu Chromium 测试配置，但未推送仓库，因此没有把未来 CI 当作已执行结果。其他网站、其他验证码形态及跨平台浏览器通过率仍需分别验收。

## 代码自评

自评范围：`src/`、`configs/`、`examples/`、`tests/`、构建和源码打包脚本。此记录是同一作者自评，不是独立审查批准。

关键不变量：只对匹配成功且无歧义的图片执行拖动；按下前检查图片；一次调用最多三次；必须正向确认成功；不携带账户登录逻辑、内部主机、数据库、真实图片或密钥；不发起模型调用。

本次未发现尚未修复的阻断问题。没有验证外部站点兼容性、异步 Playwright、Selenium、CSS background-image 或封闭 Shadow DOM；这些限制已在 [适配指南](adapting.md)列出。
