# 贡献指南

先安装 `pip install -e ".[dev]"` 和 Chromium，运行 `python -m pytest -q` 与 `python -m build`。

新算法请放在独立模块，通过纯图片接口测试，再补一个使用本地演示站的真实浏览器测试。每个网站应使用独立配置，核心库不写入账号、Cookie、授权头或站点登录步骤。

提交样本时使用合成图片或有明确公开许可的图片；不要提交实际运行的私有验证码、浏览器 profile、真实 URL 查询串和登录凭证。保持三次上限、刷新检查及正向成功证明；失败必须能返回人工路径。

修改公开 API 时同步 [README](README.md)、[适配指南](docs/adapting.md)和测试。合并前运行代码审查，记录范围、证据和未验证边界。

新增需随源码 ZIP 发布的文件时，将相对路径显式加入 `scripts/public-files.txt`；打包脚本不会自动收录目录中的其他文件。运行 `python scripts/check_docs.py` 检查文档链接，运行 `python scripts/package.py --output dist/slider-captcha-kit-v0.1.0.zip` 生成带校验清单的源码包。`BUILD-MANIFEST.json` 只在生成的 ZIP 内提供，避免仓库中保留过期文件哈希。
