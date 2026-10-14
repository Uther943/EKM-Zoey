# PPT 式讲解视频生成项目：制作总指南

本项目用代码把讲解稿做成 1920×1080 / 30fps 的 MP4 讲解视频，**会有多个视频：L0、L1、L2…**，每个视频一个文件夹 `videos/<视频>/`。
- **L0** = "Knowledge Powers AI: Understanding Knowledge Management at Lenovo"，目前已完成的全部素材和产出都属于 L0（见 `videos/L0/README.md`）
- 本文件是**所有视频共用的统一规范**（视觉、音频、流程）；具体数值都以代码为准（见各节括号里的出处）
- 每个视频自己的内容（标题、段落顺序、顶部标签文字、背景音乐、时长要求）写在 `videos/<视频>/README.md`，历次改动记在 `videos/<视频>/change_log.md`

---

## 0. 最重要的规则：先记录，再执行
- **任何变更都先登记，再去改文稿、页面、音效或代码。** 适用范围：增删页面、改旁白 / 字幕、改动画、换音效 / 背景音乐、改流程
  - 某个视频的内容改动 → `videos/<视频>/change_log.md`
  - 共用部分（流水线代码、`engine/`、`library/`、目录结构、本规范）的改动 → 根目录 `change_log.md`
- 每条记录写清：日期、段落、改了什么、改动后的页面顺序（不变就写"不变"）
- 逐段制作：一段做完给用户确认，确认后再做下一段
- 先确认在做哪个视频：命令都带 `--video <视频>`（默认 L0），文件都放进该视频自己的文件夹，不要混放
- 成片时长上限按各视频 README 的要求（写在 `video.json` 的 `limit_seconds`，不写就是 9:00；`concat.py --check` 会检查）

## 1. 整体风格
- **科技感数据可视化动画**：深色背景 + 红紫渐变光效
- **扁平几何 + 光效叠加**：圆形节点、细线连接、毛玻璃胶囊，线条纤细干净
- **无实物、无照片**：所有图形都用几何形状和线性 icon 表达
- **PPT 式讲解**：一页一个核心观点，元素随旁白逐步出现
- 文字白色、高对比；画面克制，突出内容
- **画面上的文字一律英文**；字幕中英双语（见第 10 节）

## 2. 基础参数
| 项目 | 参数 |
|---|---|
| 分辨率 / 帧率 | 1920×1080，16:9，30fps（`render.py` `FPS`） |
| 视频编码 | H.264，crf 17，preset medium，yuv420p，tv 色域（`render.py` `VIDEO_ARGS`） |
| 音频 | AAC 192k；混音为 48kHz 立体声 |
| 页面 | 每段一个 HTML，固定 1920×1080 舞台；Playwright 逐帧截图 |

## 3. 色彩（`engine/engine.css` `:root`）
| 颜色 | 色值 | 用途 |
|---|---|---|
| 深黑底 | `#0A0A0F` | 背景底色 |
| 主红 | `#E93A3A` | 核心圆、强调节点、红线、强调胶囊、icon 点缀 |
| 深紫 | `#3D1E6D` | 普通节点、背景光带 |
| 深蓝 | `#1B2F6B` | 普通节点（与深紫交替，辅助色） |
| 白色 | `#FFFFFF` | 所有文字、细连线、icon 主线条 |

- 红色只用于**重点**（核心概念 / 需要突出的那一项）
- 放在红色圆上的 icon，红色点缀改成白色，保证对比度

## 4. 字体与字号
**全片只用 Segoe UI**：`"Segoe UI", "Microsoft YaHei", sans-serif`。Segoe UI 没有中文字形，中文自动回退到 Microsoft YaHei。

| 元素 | 字号 | 字重 | 备注 |
|---|---|---|---|
| 封面主标题 | 100px | 600 | 居中 |
| 封面副标题 | 32px | 400 | 居中，上方 400×3px 红色发光分隔线 |
| 页面大标题 | 74px | 600 | 左上 (150, 110)，字距 -0.5px |
| 左侧竖排小标题 | 大标题 ×0.55（≈41px） | 600 | 见第 6 节 |
| 顶部章节标签 | 24px | 600 | 全大写，字距 3px |
| 章节卡 "CHAPTER n" | 26px | 600 | 主红，字距 6px |
| 章节卡标题 | 72px | 600 | 白色，居中 |
| 关键词胶囊 | 34px | 600 | |
| 小胶囊（成组堆叠） | 28px | 600 | |
| 节点标签 | 28px | 600 | |
| 条形图标签 | 30px | 600 | |
| 中文字幕 | 38px | 700 | |
| 英文字幕 | 28px | 700 | |

## 5. 版式与固定元素
```
┌──────────────────────────────────────────────────────────┐
│                ● KNOWLEDGE MANAGEMENT              [Logo]│  顶部：章节标签 + Logo
│  大标题（与内容同时出现，停留约 3s 后移到左侧）              │
│ │                                                         │
│竖│                                                         │
│排│               正文内容区（安全区）                         │
│标│               x 150–1840，y 90–900                       │
│题│                                                         │
│ │                                                         │
│                    中文字幕（38px）                        │  底部字幕区
│                    English subtitle (28px)               │
└──────────────────────────────────────────────────────────┘
```
| 固定元素 | 规格 |
|---|---|
| 顶部章节标签 | 顶部居中，距顶 34px；18px 白色圆点 + 标签文字（由视频决定；L0 是 `KNOWLEDGE MANAGEMENT`，目前写在 `engine/engine.js` 的 `injectChrome` 和 L0 的 `intro.html` 里，做新视频时要改成可配置） |
| 右上角 Logo | `engine/assets/lenovo.png`（所有视频共用；`engine.js` 按自身位置取，页面放在哪里都能找到）（原图 188×581），紧贴右上角（top 0 / right 0），**高 150px**，保持比例，18px 柔和红色光晕；随封面 / 章节卡淡入 |
| 左侧红线 | 每个内容页都有；x=120，y 230→870，2.5px 主红，两端 7px 红点；页面开始 0.3s 起 0.9s 画完 |
| 背景 | 深黑底 + 16 条模糊竖向光带（紫 / 红紫，缓慢漂移，blur 38px）+ 红紫大光晕 + 90 颗细小粒子缓慢上浮闪烁 + 四周暗角 |

**间距硬规则**（`check_layout.py` 会检查，不通过不能渲染）
- 所有模块（胶囊 / 标签 / 节点 / 条形图）**不得重叠**，间距 **≥12px**（`MIN_GAP`），建议 ≥20px
- 全部在安全区内：x 150–1840，y 90–900（`SAFE`）
- 大标题移走后，正文整体上移 40px（`.content { translateY(-40px) }`），视觉居中；竖排标题和红线不跟着移

## 6. 标题规则（`engine/engine.js` `DOCK`）
| 阶段 | 时间 | 效果 |
|---|---|---|
| ① 出现 | 页面开始 +0.1s | 74px 大标题在左上淡入，**与第一批内容同时出现** |
| ② 停留 | 到第一句旁白开始后 2.8s | 大标题和内容同屏，在顶部共停留约 **3s** |
| ③ 移动 | 用时 1.0s，分两步 | 前半段：在顶部缩小 + 左移 + 淡出；后半段：在红线左侧竖排淡入并轻微上滑。分两步是为了不让长标题扫过顶部章节标签 |
| ④ 停靠 | 直到本页结束 | **逆时针转 90°，从下往上读，0.55×**；沿红线垂直居中（中心 y=550），左边缘 x≈56 |

- 标题 ≤ 约 32 个字符（74px 下宽度 ≤1160px），竖排后必须落在 x ≤114、y 222–872 的区域里（`check_layout.py` 会检查）
- 大标题还在顶部时（每页前约 3.8s），**标题下方不能出现任何正文**（`check_layout.py` 会检查）

## 7. 正文元素样式（`engine/engine.css` + ENGINE 函数 `node` / `pill` / `line` / `bracket`）
| 元素 | 规格 |
|---|---|
| 核心圆 | 主红实心，r 约 110–140（常用 140），强红色光晕，可轻微呼吸 |
| 普通节点圆 | 深紫 / 深蓝交替，r 约 44–95（常用 50–80，按页面空间定；`node()` 默认 60），35% 白色描边 2px，内含白色线性 icon |
| 强调节点 | 主红实心 + 光晕，连线也用红色 |
| 节点标签 | 节点下方 14px；靠近顶部的节点标签放在节点上方 |
| 连线 | 白色 2–2.5px；强调连线红色 3px |
| 关键词胶囊 | 毛玻璃：13% 白底 + 12% 白描边 + 14px 背景模糊，圆角 30px，内边距 18/40px |
| 小胶囊组 | `.pill.sm`：28px，高约 62px，**行距 84px**；左侧配细红括线（两端 6px 红点），用白色细线连到对应节点表示归属 |
| 列表胶囊 | 左对齐，前面 12px 红色发光圆点 |
| 强调胶囊 | 主红 85% 底色（`.pill.red`） |
| 条形图 | 标签 30px；轨道高 26px、圆角 13px、10% 白底；高值用紫→红渐变，低值用白色 |
| 线性 icon | 白色粗线条约 5px（圆头）+ 主红点缀，柔和光晕；节点内 icon 约为半径的 1.2 倍 |
| 装饰 | 星形闪光 + 小圆环（白 / 红），点缀在空白处 |

## 8. 动画规范（`engine/engine.js`）
| 动画 | 参数 |
|---|---|
| 元素出现（默认 pop） | 0.6s easeOut，上移 18px → 0，缩放 0.88 → 1，淡入 |
| 线条 | 逐笔描绘，0.6–1.2s（`class="draw"`） |
| 呼吸 | 缩放 ±3%，缓慢循环（`breathe`） |
| 虚线圆环 | 匀速旋转 14°/s（`spin` / `spinr`） |
| 节点漂移 | ±6px 轻微浮动（`drift`） |
| 淡出交接 | `data-out` 指定时间点后 0.5s 淡出 |
| 换页 | 交叉淡化：进入 0.5s，退出 0.4s |
| 段首 / 段尾 | 每段开头由黑渐亮 0.4s、结尾渐暗 0.4s（`EDGE_FADE`），拼接处自然衔接 |

- **元素出现与旁白同步**：讲到哪一项，哪一项出现；不用打字机、滚动等效果
- `data-at` 写法：`s+0.3`（本页开始后）、`u3`（第 3 句开始）、`u3@across`（第 3 句说到 across 时）、`p5`（第 5 行字幕开始）、`f0.4`（该句的 40% 处）、`+0.2` / `-0.2`（偏移）

**可用的动画手法**
| 手法 | 写法 | 用途 |
|---|---|---|
| 按词出现 | `data-at="u2@Creating"` | 说到某个词的瞬间出现，逐个点亮 |
| 镜头拉远 | `data-kind="zoom"` + `data-zoom="dx,dy,scale"` + `data-origin` | 一组元素整体缩小移位，露出新一层；字幕、Logo、竖排标题、红线不缩放 |
| 光点沿曲线流动 | `class="travel"` + `data-path` | 表现知识流动 / 传递，可跨越边界 |
| 点亮涟漪 | `class="pulse"` | 节点被"接收"时变红 + 向外扩散的圆环 |
| 过渡生长 | `data-kind="bloom"` | 光点跑到目标后，目标图形从小光核长大（略带回弹）+ 一圈涟漪，避免连线末端空着 |
| 向上升起 | `data-kind="scaley"` | 从底边升起（如柱子） |
| 横向展开 | `data-kind="scalex"` / `class="grow"` | 横条、进度条展开 |
| 小元素发光 | `glowDot` 滤镜 | 光点 / 小圆用大范围柔光，避免出现方形光晕 |

## 9. 封面与章节卡
| 项目 | 封面（Intro 开头） | 章节卡（每章开头） |
|---|---|---|
| 时长 | 4.0s，无旁白 | 3.5s，无旁白（文稿 `title_card_seconds`） |
| 构成 | 红色核心圆 + 紫/蓝两侧圆 + 白色折线 + 主副标题 + 闪光装饰 | 红色核心圆（r 78，内有白色 "0n" 60px）+ 旋转虚线圆环 + 紫/蓝两侧小圆 + 白色折线 + 闪光装饰 |
| 文字 | 主标题 100px + 副标题 32px | "CHAPTER n" 26px 主红 + 章节标题 72px 白色 + 下方 300×3px 红色发光线 |
| 声音 | Intro 开场音效 | 章节转场声（见第 12 节） |

## 10. 字幕（`engine/engine.css` `#subs` + `check_subs.py`）
| 项目 | 规格 |
|---|---|
| 排列 | 中英两行：**中文在上、英文在下**，居中，固定在底部（距底 44px，两行间隔 4px） |
| 样式 | 白色加粗；**纯文字，没有底色、边框、胶囊条**，只有 1.2px 黑色投影 |
| 字号 | 中文 38px / 英文 28px |
| 切换 | 整组淡入 0.25s / 淡出 0.15s；一行字幕保持到同页下一行出现，页末多留 0.35s；不滚动、不打字机 |
| 内容 | 英文与文稿**逐字一致**；中文是忠实翻译，要用户确认 |
| 拆行 | 长句按说话的词时间拆成多行，在文稿里用 ` \| ` 标记；英文每行 **≤95 字符**（`MAX_PART`）；中文拆成相同行数；只改换行位置，不改任何文字。也可以在破折号 "—" 处换行，原文破折号两侧没有空格的（如 "asset—breaking"），拼回时不加空格（`tts.join_parts`） |

## 11. 配音与节奏（`tts.py`）
| 项目 | 参数 |
|---|---|
| 配音 | edge-tts `en-US-AriaNeural`（女声），语速 -4%（文稿 `voice` / `rate`） |
| 每页开头 | 0.5s 静音（`lead`） |
| 普通句间 | 约 0.6s（`gap` 0.45s + 裁剪后保留的首尾静音） |
| 枚举项之间 | 约 0.3s（`gap_list` 0.15s），引导句 "…is:" 与第一项之间也算 |
| 页与页之间 | 约 1.5s（`gap_slide` 0.8s + 页首 0.5s + 换页交叉淡化） |
| 段尾 | 1.5s 留白（`TAIL`） |

- 每句配音自带的首尾静音会自动裁掉，只保留 0.05s / 0.12s（`TRIM_LEAD` / `TRIM_TAIL`）
- 文稿写法（`videos/<视频>/source/scripts/<id>.json`，Intro 也一样叫 `intro.json`）：每句一个 unit，含 `slide` / `en` / `zh`
  - `"list": true`：枚举项，用短间隔
  - `"hold": {"after": "<词>", "seconds": n}`：说完这个词后本页再保持 n 秒，留给动画
  - `"pause_after": n`：这句后面额外停 n 秒
- 配音缓存在 `library/tts_cache/`（键 = 声音 + 语速 + 文字，所有视频共用），没改的句子不会重新合成。L0 的 ch1 / ch3 有一部分句子是缓存出现之前合成的，缓存里没有，重跑 `tts.py` 会联网重新合成，声音可能有细微差别

## 12. 音效（`sfx.py`）
所有音效都在旁白开始前结束，或者只放在旁白的空档里。

| 音效 | 规格 |
|---|---|
| **Intro 开场** | 4.8s：上扬气流（0–1.0s）→ 标题出现时低频冲击（1.0s）→ 钟鸣般闪光音，红线出现时一声高音（1.4s）→ 低音 pad + 混响尾巴，淡出；峰值 **-6dBFS**（`PEAK_DB`），和旁白差不多响 |
| **章节转场声** | 直接用 `library/transition/orig_low_v1.wav`（`TR_FILE`），2.6s，峰值 **-12dBFS**：短气流（0–0.6s，上限 4.5kHz）→ "CHAPTER n" 出现时（0.6s）柔和低频 + 两声"叮"（880 / 1319Hz，相隔 0.12s，起音 8ms，泛音很弱），整体 6kHz 低通，混响尾巴淡出 |
| **到达音"叮"** | 光点抵达节点（节点变红 + 涟漪）时一声清脆短"叮"：正弦 + 少量泛音，起音 3ms，衰减约 0.3s，轻混响，峰值 **-14dBFS**（`DING_PEAK_DB`）；连续几次到达时音高逐级升高（如 1568 → 1760 → 2093Hz） |

- 正文默认不加音效
- "叮"的写法：在文稿 json 里加 `"sfx"` 列表，时间语法和画面 `data-at` 相同，例如 `{"kind": "ding", "at": "u0@across+2.5", "pitch": 1568}`；时间 = 对应光点动画的 at + dur
- `sfx.py` 输出：`build/audio/sfx_<id>.wav`（音效本身）和 `build/audio/<id>_mix.wav`（旁白 + 音效，48kHz 立体声）；改了配音后要重跑

**音效制作方法：在 `library/transition/` 试听新版本**（不影响任何现有文件）
```
library/transition/
├─ orig_low_v1.wav    正在用的章节转场声
├─ transition.py      参数化生成器（自带滤波 / 混响，不 import sfx.py）
├─ presets.json       每个版本一项：钟声音高、和弦、起音 / 衰减、明亮度、气声 / 低频量、混响、长度、峰值，以及可选的电钢琴音色和反向拉起
└─ preview/           试听输出（不是视频 build/ 里放画面预览图的 preview/）
   ├─ current.wav       换之前的旧转场声，用来对比
   ├─ <名字>.wav         只有这版音效
   ├─ <名字>_ch2.wav     叠上 ch2 开头约 10 秒旁白
   └─ <名字>_ch2_bgm.wav 再叠上成片的背景音乐（加 --bgm）
```
1. 在 `presets.json` 里加一项（或改数字），不用改代码
2. 运行 `python library/transition/transition.py --bgm [--video L0] <名字> [<名字> ...]`，只读该视频的 ch2 旁白和成片混音，只写 `preview/`
3. 用户选定后：把 `preview/<名字>.wav` **原样复制**到 `library/transition/`（重新生成的话噪声会不同），`sfx.py` 的 `TR_FILE` 指向它，然后对所有章节重跑 `sfx.py` → `render.py --remux` → `bgm.py --full ...`

## 13. 背景音乐（`bgm.py`）
背景音乐原曲放共用的 `library/music/`；生成的文件（音乐 stem、带音乐的混音、试听片段）放各视频的 `build/bgm/`，单段配乐试验视频放 `output/trials/`。

- **一条音乐铺满全片**（从 Intro 第 0 秒到收尾），用哪首由视频决定（L0：`library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3`，146.7 BPM，每小节 1.636s；新曲目要在 `bgm.py` 的 `TRACKS` 里登记小节参数）
- **剪法**：按小节重排：前奏 → 主体小节循环 → 过渡小节 → **副歌正好落在收尾页的第一拍** → 终音与尾音；接口处 40ms 交叉淡化，开头 0.5s 淡入、结尾 0.5s 淡出
- **章节卡**：每张章节卡开始前 0.4s 起，音乐逐渐变闷（700Hz 低通）并低 3dB，到卡片 2.5s 后开始恢复，3.5s 完全恢复（`CARD_DIP` / `CARD_LP_HZ` / `CARD_DB`）
- **电平**：停顿时音乐比旁白低约 10dB（`GAP_DB`），说话时再压 8dB，约低 18dB（`DUCK_DB`）；音乐 1–4kHz 衰减 4dB 给人声让位（`MID_CUT_DB`）；峰值 ≤ -1dBFS（`PEAK_LIMIT_DB`）
- 底轨用各段的 `build/audio/<id>_mix.wav`（旁白 + 音效，不含音乐），音乐只铺一层
- 另有两种可选风格：`--tag v2`（自己合成、同调性、逐章加层、音量逐章上升）和 `--style remix --tag v3`（只用原曲音频，按章节重排小节）

## 14. 内容规则
- **画面文字必须用旁白原词**：可以缩短，不能换同义词（旁白说 "difficult to find"，画面写 "Difficult to Find"，不能写 "Hard to Find"）；用户指定的用词例外要记进该视频的 `change_log.md`
- 一页一个核心观点，关键词不超过 7 个；标题约 32 个字符以内
- 不手改英文字幕：改 `source/scripts/<id>.json` 后重新生成

## 15. 常用页面版式
| 版式 | 适用场景 | 构成 |
|---|---|---|
| 封面 | 段落开头 | 红色核心圆 + 紫/蓝两侧圆 + 白色折线 + 主副标题 + 闪光装饰 |
| 中心辐射 | 一个主题分出多项 | 中心核心圆 + 4 个节点 + 连线；某一项展开成小胶囊组 |
| 散点网络 | 来源 / 分布广泛 | 中心节点 + 周围 6–7 个节点，最关键的一项用红色强调 |
| 列表 + 对比 | 问题 / 痛点 / 数据对比 | 左侧胶囊列表 + 中间焦点 icon + 右侧条形对比 |
| 汇聚流向 | 输入 → 结果 / 因果关系 | 左侧节点群 → 流动曲线 → 右侧核心圆环 + 结论胶囊 |

## 16. 项目结构
```
<根目录>/
├─ CLAUDE.md  README.md  change_log.md     共用规范 / 结构说明 / 共用部分的改动记录
├─ sections.py tts.py check_subs.py sfx.py check_layout.py render.py concat.py bgm.py
│                                           流水线代码（所有视频共用；路径都由 sections.paths() 给出）
├─ engine/                                  共用页面引擎：engine.js、engine.css、assets/lenovo.png
├─ library/                                 共用素材库
│  ├─ music/                                背景音乐原曲
│  ├─ transition/                           章节转场声：在用的 wav、生成器 transition.py、presets.json、试听 preview/
│  └─ tts_cache/                            配音缓存
└─ videos/
   └─ <视频>/                               L0、L1 …
      ├─ README.md                          本视频说明：标题、段落顺序、顶部标签文字、背景音乐、时长要求
      ├─ video.json                         {"order": [...]}：成片包含哪些段、按什么顺序（concat.py / bgm.py --full 读它）
      ├─ change_log.md                      本视频的改动记录
      ├─ source/                            素材（人写的）
      │  ├─ scripts/<id>.json               文稿
      │  └─ slides/<id>.html                页面
      ├─ build/                             中间文件（都能重新生成）
      │  ├─ timelines/                      <id>.json、timeline_<id>.js（时间轴）
      │  ├─ audio/                          <id>.wav、sfx_<id>.wav、<id>_mix.wav、units/<id>/（旁白、音效、混音、逐句配音）
      │  ├─ bgm/                            背景音乐 stem、带音乐的混音、试听片段
      │  ├─ preview/                        预览帧 <id>_<t>.png
      │  └─ _seg/                           并行渲染临时分段
      ├─ output/                            产出：<id>.mp4（各段）、full.mp4（成片）、trials/（试验片）
      ├─ backup/                            旧版备份（可选）
      └─ experiments/                       独立试验（可选，如 L0 的 kokoro/）
```
- 段 id：`intro`（不带 `--section` 时）、`ch1`、`ch2` … `closing`；所有视频的 Intro 都按普通段落命名，不再有特例
- 页面在 `source/slides/` 里，引用共用引擎写 `../../../../engine/engine.css` / `engine.js`，引用时间轴写 `../../build/timelines/timeline_<id>.js`（照抄现有页面即可）
- 新建视频：**先按根目录 `README.md` 第 0 节提问**（两轮选择题：内容结构、声音外观），答案确认后建 `videos/<视频>/`，写 `README.md`、`video.json`、`change_log.md`，再按第 17 节逐段做

## 17. 制作流程与命令
```
videos/<视频>/change_log.md 先登记
  → source/scripts/<id>.json   文稿
  → tts.py              配音 + 词时间 → build/audio/<id>.wav、build/timelines/<id>.json + timeline_<id>.js
  → check_subs.py       英文字幕 == 原文，每行 ≤95 字符
  → sfx.py              转场声 / 开场音效 / "叮" → build/audio/<id>_mix.wav
  → source/slides/<id>.html   只写页面内容；共用 engine/engine.js + engine.css（L0 的 intro.html 自带一份内联引擎，按同样规则维护）
  → check_layout.py     重叠、安全区、竖排标题位置、标题下方有没有内容
  → render.py --preview 抽关键帧检查观感、对比度、字幕位置
  → render.py           逐帧渲染 → output/<id>.mp4
  → bgm.py --full       按 video.json 拼接全片 + 铺一条背景音乐 → output/full.mp4
```
```
# 每个脚本都用 --video <视频>（默认 L0）和 --section <id>（不带就是 intro）
python tts.py --section ch1                      # 配音 + 时间轴
python check_subs.py --section ch1               # 字幕核对
python sfx.py --section ch1                      # 音效 + 混音（改配音后要重跑）
python check_layout.py --section ch1             # 版面检查，必须通过才能渲染
python render.py --section ch1 --preview 3,12    # 预览帧 -> build/preview/ch1_<t>.png
python render.py --section ch1 --workers 8       # 完整渲染 -> output/ch1.mp4（每段约 1.5–2 分钟）
python render.py --section ch1 --remux           # 只换音轨，几秒
python concat.py --check                         # 打印各段时长和成片总长
python bgm.py --full --track "library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3"
                                                 # 成片 -> output/full.mp4；任何一段重新渲染或换音轨后都要重跑
python bgm.py --full --tag v2                    # 可选：合成配乐版 -> output/full_v2.mp4（L0 的成片已删，素材在 build/bgm/）
python bgm.py --full --track "library/music/morrix…511750.mp3" --style remix --tag v3
                                                 # 可选：原曲重剪版 -> output/full_v3.mp4（同上）
python library/transition/transition.py --bgm <名字>   # 试听新转场声（见第 12 节）
python tts.py --video L1 --section ch1           # 其他视频：加 --video
```
- 新段落一律复用 `engine/engine.js` / `engine.css` 和 ENGINE 函数（`node` / `pill` / `line` / `bracket`）
