# 网站适配指南

> 状态：active
>
> 权威范围：Slider Captcha Kit 0.1.0 配置和扩展接口
>
> 维护责任：项目贡献者
>
> 最近核验：2026-11-18

## 先确定图片类型

| 页面特征 | 适配方式 |
| --- | --- |
| 拼图透明层与背景等高，纵向位置已保留，轮廓为白色 | `outline`，`piece_y` 自动为 0 |
| 拼图是小图，保留与缺口对应的纹理 | `template`，指定或推算 `piece_y` |
| 缺口区域只降低了原纹理亮度 | 可测试 `template` 的归一化相关性 |
| 图片由 Canvas 绘制 | 选择实际 `<canvas>` 节点 |
| 图片通过 CSS background-image、WebGL、封闭 Shadow DOM 绘制 | 当前 DOM 适配器未直接支持；获取获授权图片字节后使用纯图片接口或编写自己的采集适配器 |
| 旋转、点选、重排、二维移动或只有行为验证 | 当前算法不适用 |

轮廓算法来自此前实际采集流程的本地匹配实现；通用适配器和纹理算法在本项目合成样本及本地演示中验证。没有逐个验证所有外部验证码供应商，也没有通用通过率承诺。

## 配置选择器

复制 [站点模板](../configs/site.example.json)，在浏览器开发工具中确认每个选择器只匹配当前可见挑战的对应节点。不同挑战应分别保存配置。

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `background` | 是 | 背景 `<img>` 或 `<canvas>` |
| `piece` | 是 | 透明拼图 `<img>` 或 `<canvas>` |
| `handle` | 是 | 可拖动按钮 |
| `success` | 是，或传 Python 回调 | 网站确认本次验证后才显示的节点 |
| `panel` | 否 | 背景的实际显示矩形；默认背景节点，避免选有 padding 的外框 |
| `piece_container` | 否 | 实际移动拼图的矩形；默认拼图节点 |
| `refresh` | 否 | 更换图片按钮 |
| `failure` | 否 | 本次验证被拒绝时可见的节点，不要选永远存在的隐藏错误容器 |
| `frame` | 否 | iframe 的 CSS 选择器；省略时扫描主页面与各 frame |
| `piece_y` | 否 | 拼图在背景原图中的纵向坐标，单位为原图像素 |
| `drag_ratio` | 否 | 鼠标距离 / 拼图距离，默认 1；仅在实际量过比例后设置 |

成功节点如果在 iframe 外，可省略 `frame` 让适配器扫描，或传入 Python `success(page)` 回调。嵌套 iframe 可使用自动扫描；显式 `frame` 仅定位对应页面根下的 iframe。

页面使用普通图片时，通过已登录浏览器内的 Canvas 读取像素。跨域服务器若没有授予相应 CORS 权限，读取会失败并返回人工状态；本库不会额外下载 Cookie、导出会话或伪造权限。

## 选择图片算法

默认：

```json
{"method":"outline","min_score":0.8,"min_margin":0.03,"candidate_separation":1}
```

轮廓使用透明度 >200、拼图 RGB 最小通道 >180、背景 RGB 最小通道 >160 的像素进行水平比较。可通过 `alpha_threshold`、`piece_white_threshold`、`background_white_threshold` 按样本调整。

纹理模式：

```json
{"method":"template","min_score":0.8,"min_margin":0.03,"candidate_separation":3}
```

纹理算法只比较不透明区域，对 RGB 各通道去均值，再计算归一化相关性。`candidate_separation` 是比较次优候选时排除相邻峰的距离；默认为 1，代表严格比较每一个相邻位置。宽峰样本可能需要 2–3，但应先用有人工标注的样本验证。不要为了“通过”直接降低阈值或扩大排除距离。

`MatchError` 表示不可靠或不支持，`AmbiguousMatch` 是其子类；异常的 `result` 可包含安全的匹配数值。图像上限：单文件 4 MB、单边 4096、总像素 4,194,304；候选位置数乘有效匹配像素超过 5,000 万时拒绝暴力搜索；格式 PNG/JPEG/WebP。透明拼图通常使用 PNG。

## 自定义算法

接口为：

```python
def my_matcher(background_bytes, piece_bytes, *, piece_y, options):
    # 返回 MatchResult；不可靠时抛 MatchError。
    ...

result = solve(page, config, matcher=my_matcher)
```

`MatchResult` 字段为 `offset_x`、`score`、`runner_up_score`、`background_width`、`piece_width`、`piece_y`、`method`。自定义 matcher 应自行实施置信度、歧义和输入校验；适配器不会自动将某个任意分数解释为可靠结果。

适配器不负责初始化浏览器、持久化 Cookie、登录账号或后续业务动作。现有 Selenium/其他框架可复用 `match_images` 与 `trajectory.drag_points`，但当前没有随包提供这些框架的浏览器适配器。

## 结果处理

| `status` | 含义 |
| --- | --- |
| `solved` | 实际尝试后，成功节点/回调已确认，且挑战已消失 |
| `already_passed` | 调用时已处于成功状态，没有新拖动 |
| `manual` | 未找到挑战、分数低、歧义、刷新、异常或服务器未确认，调用方需要决定是否等待人工 |
| `disabled` | 本次调用关闭自动尝试 |

最多三次是一次 `solve` 调用的上限。调用方不应通过无限重复 `solve` 来绕开该上限；原定时任务仍应按自身重试策略运行。

只有 Python 同步 Playwright 适配器；异步调用方可写自己的适配层，或者在独立线程/进程内管理整套同步浏览器生命周期，不要跨线程共享 page。
