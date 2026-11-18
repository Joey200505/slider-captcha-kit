# 第三方依赖

项目自身代码使用 [MIT](LICENSE)。依赖不作为源码复制到本项目中，安装时由包管理器获取，使用各自许可证：

| 依赖 | 用途 | 许可证 |
| --- | --- | --- |
| NumPy | 像素数组与匹配计算 | 主许可 BSD-3-Clause，发行包另含所附组件许可 |
| Pillow | 图片解码与合成夹具 | MIT-CMU |
| Playwright for Python（可选） | 浏览器驱动 | Apache-2.0 |
| pytest（开发依赖） | 自动化测试 | MIT |

具体许可证以所安装发行包随附的许可文件为准。图片夹具由本项目 [synthetic.py](src/slider_captcha_kit/synthetic.py)生成，未附带任何实际网站原图。
