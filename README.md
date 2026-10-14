# 讲解视频生成项目：项目说明

## 0. 新视频开工：先问清楚再动手

用户说"做一个新视频"（或者给了一份新讲解稿）时，**先按本节问清楚、登记好，再动手**。

### 0.1 怎么问
- **用选择题问**（Claude Code 里用 AskUserQuestion）：每题 2–4 个选项，**默认项排第一，标"(默认)"**；用户也可以选"其他"自己写
- **分两轮，每轮最多 4 题**：第一轮定内容和结构（0.2），第二轮定声音和外观（0.3）。第二轮的默认值都和 L0 一样，用户回一句"都用默认"就可以跳过
- 用户已经说过的、讲解稿里写明的，不再问；拿不准的不要猜，问
- 问完把所有答案汇总成一张表给用户确认，确认后写进 `videos/<视频>/README.md` 的概况表，并作为 `videos/<视频>/change_log.md` 的第一条（"新建视频"）

### 0.2 第一轮：内容和结构
| # | 问题 | 选项（第一个是默认） | 决定什么 |
|---|---|---|---|
| 1 | 视频编号和标题 | 下一个空编号（如 L1）+ 讲解稿标题 / 其他 | 文件夹 `videos/<视频>/`、封面主标题 |
| 2 | 讲解稿从哪来 | 用户给完整英文稿，逐字使用 / 用户给要点，Claude 起草英文稿后确认 / 用户给中文稿，Claude 译成英文后确认 | 旁白和英文字幕（与定稿逐字一致） |
| 3 | 是否分章节 | **分章**：`intro` + `ch1`…`chN` + `closing` / **不分章**：只有 `intro` + `closing` 两段 | 段落列表、`video.json`、有几张章节卡 |
| 4 | 时长上限 | ≤ 9:00（同 L0） / 其他 | `video.json` 的 `limit_seconds`（不写就是 9:00） |

**分章（默认）**：Intro 开头是 4s 封面 + 开场音效；每章开头一张 3.5s 章节卡（"CHAPTER n" + 章节标题）+ 转场声；最后是 Closing，背景音乐的副歌落在它的收尾页。章节按讲解稿的大标题切，Claude 先列出切法给用户确认。

**不分章**：正文全放在 Intro 里连续讲，中间没有章节卡；Closing 开头仍有一张 "CLOSING" 卡。代码默认第一段以外的每段开头都有卡（`tts.py` 的 `title_card_seconds`、`sfx.py` 的转场声、`bgm.py` 在每段开头让音乐变闷），所以不要在 Intro 和 Closing 之间再插不带卡的段。

### 0.3 第二轮：声音和外观（默认都和 L0 一样）
| # | 问题 | 默认 | 其他选项 |
|---|---|---|---|
| 5 | 背景音乐 | `library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3`：一条铺满全片，副歌落在收尾页第一拍，章节卡处变闷，说话时自动压低（`bgm.py --full`） | 换一首：放进 `library/music/`，在 `bgm.py` 的 `TRACKS` 登记小节参数（`d0` 第一小节起点、`bar` 小节长度、`pieces` 剪法、`s3_bar` 副歌小节）/ `--tag v2` 合成配乐 / `--style remix --tag v3` 原曲重剪 / 不要背景音乐（用 `concat.py` 出片） |
| 6 | 音效 | Intro 开场音效 + 章节转场声 `library/transition/orig_low_v1.wav`；光点到达节点时一声"叮" | 换转场声（先在 `library/transition/` 试听选定，见 CLAUDE.md 第 12 节）/ 不要"叮" |
| 7 | 配音 | edge-tts `en-US-AriaNeural` 女声，语速 -4% | 换声音（如男声 `en-US-GuyNeural`）/ 调语速 |
| 8 | 顶部标签和 Logo | 标签：Claude 按主题提一个全大写短词（L0 是 `KNOWLEDGE MANAGEMENT`）；Logo：联想 `engine/assets/lenovo.png` | 用户指定标签文字 / 换 Logo / 不要 Logo |

注意：顶部标签目前写死在 `engine/engine.js` 的 `injectChrome` 里。新视频的标签和 L0 不同时，要先在根目录 `change_log.md` 登记、把它改成按视频配置，并确认 L0 不受影响。换 Logo、不分章以外的特殊结构也一样，先登记再改共用代码。

### 0.4 不用问（全片固定，见 [CLAUDE.md](CLAUDE.md)）
1920×1080 / 30fps；视觉风格、颜色、字体字号、版式、动画；画面文字全英文，并且用旁白原词；字幕中英双语（中文在上），中文由 Claude 翻译、用户确认。用户主动要求改这些时，按例外记进该视频的 `change_log.md`。

### 0.5 制作步骤（✔ = 停下来等用户确认）
| 步 | 做什么 | 产出 | 确认 |
|---|---|---|---|
| 1 | 两轮提问，汇总答案 | 答案表 | ✔ 答案表 |
| 2 | 需要改共用代码的（新标签、新曲目等），先在根目录 `change_log.md` 登记，再改 | 代码改动 | — |
| 3 | 建 `videos/<视频>/`：`README.md`（概况表）、`video.json`、`change_log.md`（第一条：新建视频 + 答案表） | 视频文件夹 | — |
| 4 | **段落大纲**：把讲解稿切成段（`intro` / `ch1`… / `closing`），列出每段几页、每页标题（≤32 字符）、核心观点和关键词（≤7 个）、预计时长。收尾段的最后一页编号要是 `S3`（`bgm.py` 把副歌对在最后一段的 `S3` 页上；页数不同时要先改 `bgm.py`） | 大纲表，写进视频 README 的"段落顺序" | ✔ 大纲 |
| 5a | 逐段制作，从 `intro` 开始：写文稿 `source/scripts/<id>.json`（`en` + `zh`，长句拆行） | 文稿 | ✔ 中文翻译和拆行 |
| 5b | `tts.py` → `check_subs.py` → `sfx.py` | 配音、时间轴、混音 | — |
| 5c | 写页面 `source/slides/<id>.html` → `check_layout.py` → `render.py --preview` | 预览帧 | ✔ 预览帧 |
| 5d | `render.py --workers 8` | `output/<id>.mp4` | ✔ 本段视频，确认后才做下一段 |
| 6 | 所有段落确认后：`concat.py --check` 看总长 → `bgm.py --full` | `output/full.mp4` | ✔ 成片 |
| 7 | 收尾：更新视频 README（状态、成片时长、各段时长）和下面的视频表 | 文档 | — |

---

用代码把讲解稿做成 1920×1080 / 30fps 的 MP4 讲解视频。项目里会有多个视频（L0、L1、L2…），每个视频一个文件夹，共用同一套代码、页面引擎、素材库和制作规范。

| 视频 | 内容 | 状态 | 说明 |
|---|---|---|---|
| **L0** | Knowledge Powers AI: Understanding Knowledge Management at Lenovo | 已完成，成片 `videos/L0/output/full.mp4`（5:32） | [videos/L0/README.md](videos/L0/README.md) |
| **Trainning** | From Code to Video（视频是怎么用代码做出来的） | 已完成，成片 `videos/Trainning/output/full.mp4`（2:10） | [videos/Trainning/README.md](videos/Trainning/README.md) |

- **制作规范**（颜色、字号、动画、节奏、音效、目录约定等所有参数）：[CLAUDE.md](CLAUDE.md)，所有视频共用
- **改动记录**：
  - 某个视频的内容 → `videos/<视频>/change_log.md`
  - 共用部分（代码、引擎、素材库、结构）→ [change_log.md](change_log.md)
  - 任何改动都先登记，再执行

本文件讲新视频开工前要问什么（第 0 节）、目录和文件的作用，以及整条链路怎么串起来，不重复参数。

---

## 1. 核心思路：视频是怎么"用代码做出来"的

1. **每一段都是一个网页。** `videos/<视频>/source/slides/<id>.html` 里摆好这一段的所有元素（标题、圆、线、胶囊、icon、字幕）；共用的样式和动画引擎在 `engine/engine.css` / `engine/engine.js`。
2. **画面按时间算出来，不是实时播放。** 引擎提供 `renderAt(t)`：给它任意时间 t（秒），它就把这一时刻每个元素的位置、透明度、缩放算好画出来。同一个 t 永远得到同一帧，所以可以一帧一帧精确截图。
3. **所有时间都来自配音。** `tts.py` 合成旁白时，会拿到每个英文单词说出的时间。页面里的元素写 `data-at="u3@across"`，意思是"第 3 句说到 across 这个词时出现"，所以画面和旁白自然同步，字幕也按这些时间切换。
4. **截图 → 视频。** `render.py` 用 Playwright 打开无头 Chromium，从第 0 帧到最后一帧依次调 `renderAt(帧号 / 30)` 并截图，把图片流交给 ffmpeg 编码成 H.264，再装上混好的音轨，得到 `output/<id>.mp4`。
5. **拼成成片。** `bgm.py --full` 按 `video.json` 里的顺序把各段 MP4 拼起来（画面直接拷贝，不重新编码），把各段音轨接成一条，再铺一条自动避让旁白的背景音乐，得到 `output/full.mp4`。

---

## 2. 目录结构

```
<根目录>/
├─ CLAUDE.md  README.md  change_log.md     共用规范 / 本说明 / 共用部分的改动记录
├─ *.py                                     流水线代码（所有视频共用）
├─ engine/                                  共用页面引擎 + Logo
├─ library/                                 共用素材库：背景音乐原曲、转场声、配音缓存
└─ videos/
   └─ L0/                                   一个视频 = 一个文件夹
      ├─ README.md  video.json  change_log.md  narration_script.md
      ├─ source/    素材（人写的）：文稿、页面
      ├─ build/     中间文件（都能重新生成）：时间轴、配音、音效混音、背景音乐 stem、预览帧
      ├─ output/    产出：各段 MP4、成片 full.mp4、试验片 trials/
      ├─ backup/    旧版备份
      └─ experiments/  独立试验
```

**判断一个文件该放哪：**
- 所有视频都用 → 根目录的 `engine/` 或 `library/`
- 只属于某个视频、是人写的 → `source/`
- 由脚本生成、删了能重建 → `build/`
- 最终要交付或观看的视频 → `output/`

---

## 3. 链路图（以 `videos/<v>/` 为相对路径）

```
 ① 文稿                              ② 配音 + 时间轴                              ③ 音效混音
 source/scripts/<id>.json ─tts.py─▶ build/audio/units/<id>/*.mp3/.wav （逐句配音）
                                    build/audio/<id>.wav              （整段旁白）  ─sfx.py─▶ build/audio/sfx_<id>.wav  （音效本身）
                                    build/timelines/<id>.json         （时间轴）              build/audio/<id>_mix.wav （旁白 + 音效）
                                    build/timelines/timeline_<id>.js  （给网页用）                   │
                                          │                                                       │
               check_subs.py ◀────────────┤  英文字幕 == 原文？                                     │
                                          ▼                                                       │
 ④ 页面                                                                                           │
 source/slides/<id>.html + engine/engine.js + engine/engine.css + build/timelines/timeline_<id>.js  │
        │                                                                                         │
        ├── check_layout.py        重叠 / 安全区 / 标题位置检查                                    │
        ├── render.py --preview    抽几帧 → build/preview/<id>_<t>.png                            │
        ▼                                                                                         │
 ⑤ 渲染                                                                                           │
 render.py --workers 8 ── 8 个浏览器并行截图 → build/_seg/ 分段 ── 拼接 + 装音轨 ◀───────────────────┘
        │
        ▼
 output/<id>.mp4
        │
        ▼
 ⑥ 成片
 bgm.py --full --track "library/music/<曲目>.mp3"
        ├─ 按 video.json 的 order 拼接各段画面（直接拷贝）
        ├─ 把各段 build/audio/<id>_mix.wav 接成一条
        ├─ 按小节剪接背景音乐，副歌对齐收尾页，章节卡处变闷，说话时自动压低
        ▼
 build/bgm/bgm_full.wav       （背景音乐 stem）
 build/bgm/full_bgm_mix.wav   （成片混音）
 output/full.mp4              （正式成片）
```

---

## 4. 分步说明：先生成什么，再生成什么

所有命令都在根目录运行。`--video` 默认是 L0，`--section` 不写就是 intro。

| 步骤 | 命令 | 读入 | 生成 | 为什么排在这里 |
|---|---|---|---|---|
| ① 写文稿 | （手写） | — | `source/scripts/<id>.json` | 每句一个 unit：所属页面 `slide`、英文 `en`、中文 `zh`；` \| ` 拆字幕行，`list` / `hold` / `pause_after` 控制节奏，`sfx` 写"叮"的位置 |
| ② 配音 + 时间轴 | `python tts.py --section <id>` | 文稿 | `build/audio/units/<id>/`、`build/audio/<id>.wav`、`build/timelines/<id>.json` + `timeline_<id>.js` | **必须最先跑**：整段多长、每页从几秒开始、每个词几秒说出，都由它决定，后面所有步骤都依赖这些时间。合成过的句子缓存在 `library/tts_cache/`，没改的不会重新合成 |
| 检查字幕 | `python check_subs.py --section <id>` | 文稿 | （只打印结果） | 英文字幕拼回去必须和原文逐字一致，每行不超长 |
| ③ 音效混音 | `python sfx.py --section <id>` | 旁白、时间轴、`library/transition/orig_low_v1.wav` | `build/audio/sfx_<id>.wav`、`build/audio/<id>_mix.wav` | 要知道旁白多长、"叮"落在哪个词上，所以排在配音之后。intro 用合成的开场音效，章节用转场声文件 |
| ④ 写页面 | （手写） | 时间轴 js、engine | `source/slides/<id>.html` | 元素用 `data-at` 挂在页面开始 / 第几句 / 某个词上 |
| 版面检查 | `python check_layout.py --section <id>` | 页面 | （只打印结果） | 在真实浏览器里量每个元素的位置：不重叠、不出安全区、竖排标题放得下、大标题下方没有内容。**不通过不能渲染** |
| 预览 | `python render.py --section <id> --preview 3,12` | 页面 | `build/preview/<id>_<t>.png` | 全量渲染要几分钟，先抽几帧看观感、对比度、字幕位置 |
| ⑤ 渲染 | `python render.py --section <id> --workers 8` | 页面、`build/audio/<id>_mix.wav` | `output/<id>.mp4`（中间分段在 `build/_seg/`，用完自动删除） | 每段约 1.5–2 分钟 |
| ⑥ 成片 | `python bgm.py --full --track "library/music/<曲目>.mp3"` | `video.json`、各段 MP4 和混音、背景音乐原曲 | `build/bgm/bgm_full.wav`、`build/bgm/full_bgm_mix.wav`、`output/full.mp4` | 要等所有段落都做好；任何一段改了都要重跑这一步 |

其他命令：
- `python concat.py --check`：打印各段时长和总长
- `python concat.py`：只拼接、不加背景音乐，快速检查用。它也输出到 `output/full.mp4`，会覆盖正式成片，用完记得重跑 `bgm.py --full`
- `python render.py --section <id> --remux`：只换音轨不重画画面，几秒完成
- 做其他视频：每条命令加 `--video L1`

---

## 5. 改了什么，要重跑哪几步

| 改动 | 要重跑 |
|---|---|
| 改旁白 / 字幕文字 | `tts.py` → `check_subs.py` → `sfx.py` → 页面里时间对不上的地方调一下 → `check_layout.py` → `render.py` → `bgm.py --full` |
| 只改画面 / 动画 | `check_layout.py` → `render.py --preview` → `render.py` → `bgm.py --full` |
| 只换音效（转场声、"叮"） | `sfx.py` → `render.py --remux` → `bgm.py --full` |
| 只换背景音乐 | `bgm.py --full` |
| 新加一段 | 全流程；并把新段落的 id 加进该视频 `video.json` 的 `order` |
| 换转场声 | 先在 `library/transition/` 试听选定（见 CLAUDE.md 第 12 节），再对每个章节跑 `sfx.py` → `render.py --remux`，最后 `bgm.py --full` |
| 改共用引擎 `engine/` | 会影响**所有视频**：每个视频都要 `check_layout.py` → `render.py`，确认没有意外变化 |
| 新建一个视频 | 建 `videos/<视频>/`，写 `README.md`、`video.json`、`change_log.md`，再逐段走全流程（见 CLAUDE.md 第 16、17 节） |

---

## 6. 每个文件 / 目录的作用

### 根目录：脚本（所有视频共用）
| 文件 | 作用 |
|---|---|
| `sections.py` | 路径约定：`paths(section, video)` 给出一段的所有文件位置，`order(video)` 读 `video.json`；所有脚本的 `--video` / `--section` 都从这里解析 |
| `tts.py` | 逐句调 edge-tts 合成英文旁白，拿到词时间，按节奏规则拼接，输出整段旁白和时间轴 |
| `check_subs.py` | 检查英文字幕和原文逐字一致、每行不超长 |
| `sfx.py` | 生成 intro 开场音效；章节读入转场声文件；按文稿 `sfx` 列表放"叮"；和旁白混成 `<id>_mix.wav` |
| `check_layout.py` | 用浏览器量出页面元素位置，检查重叠、安全区、标题 |
| `render.py` | 预览帧、逐帧渲染成 MP4、只换音轨（`--remux`） |
| `concat.py` | 拼接各段（不加音乐）、`--check` 看时长 |
| `bgm.py` | 背景音乐：`--full` 生成成片；`--tag v2` 是自己合成的配乐版；`--style remix --tag v3` 是原曲重剪版；`--section closing` 是早期单段配乐试验 |

### 根目录：文档
| 文件 | 作用 |
|---|---|
| `CLAUDE.md` | 制作总指南：所有视频共用的规范、参数、目录约定、流程、命令。Claude 每次对话都会自动读它 |
| `README.md` | 本文件：目录、文件作用、生成链路 |
| `change_log.md` | 共用部分（代码、引擎、素材库、结构）的改动记录 |

### 根目录：共用引擎和素材库
| 目录 / 文件 | 作用 |
|---|---|
| `engine/engine.js` | 共用动画引擎：`renderAt(t)`、`data-at` 解析、标题停靠、字幕、背景、ENGINE 函数（`node` / `pill` / `line` / `bracket`）、icon 库 |
| `engine/engine.css` | 共用样式：颜色、字体、标题、胶囊、章节卡、字幕 |
| `engine/assets/lenovo.png` | 右上角联想 Logo（`engine.js` 按自身位置引用） |
| `library/music/` | 背景音乐原曲（现在只有 morrix…511750.mp3） |
| `library/transition/` | 章节转场声：在用的 `orig_low_v1.wav`、试听生成器 `transition.py`、各版本参数 `presets.json`、试听输出 `preview/` |
| `library/tts_cache/` | 配音缓存，所有视频共用，避免重复合成 |

### 每个视频：`videos/<视频>/`
| 文件 / 目录 | 作用 |
|---|---|
| `README.md` | 这个视频的说明：标题、段落顺序、时长、背景音乐、特别约定 |
| `video.json` | `{"order": [...]}`：成片包含哪些段、按什么顺序 |
| `change_log.md` | 这个视频的改动记录 |
| `source/scripts/<id>.json` | 文稿（人写） |
| `source/slides/<id>.html` | 页面（人写） |
| `build/timelines/` | `<id>.json`（给脚本用）、`timeline_<id>.js`（给页面用），由 tts.py 生成 |
| `build/audio/` | `<id>.wav` 整段旁白、`units/<id>/` 逐句配音（tts.py）；`sfx_<id>.wav` 音效、`<id>_mix.wav` 旁白 + 音效（sfx.py） |
| `build/bgm/` | 背景音乐 stem、带音乐的混音、试听片段（bgm.py） |
| `build/preview/` | 预览帧（render.py --preview） |
| `build/_seg/` | 并行渲染的临时分段 |
| `output/<id>.mp4` | 各段视频（带旁白 + 音效，不带背景音乐） |
| `output/full.mp4` | **正式成片** |
| `output/trials/` | 试验片 |
| `backup/`、`experiments/` | 旧版备份、独立试验（可选） |

L0 里具体有哪些文件，见 [videos/L0/README.md](videos/L0/README.md)。

---

## 7. 环境依赖

### 安装
```
pip install edge-tts aiohttp playwright imageio-ffmpeg numpy scipy
python -m playwright install chromium
```

### 清单（括号里是目前在用的版本，Python 3.13.12）
| 依赖 | 版本 | 谁用 | 用途 |
|---|---|---|---|
| Python | 3.13 | 全部 | 3.10 以上应该都行，没有测过 |
| `edge-tts` | 7.2.8 | tts.py | 微软在线语音合成 + 词时间 |
| `aiohttp` | 3.14.4 | tts.py | edge-tts 的网络层；服务器返回 403 时，tts.py 靠它识别错误并换下一个服务地址 |
| `playwright` | 1.63.0 | render.py、check_layout.py | 打开无头 Chromium 逐帧截图、量元素位置 |
| Chromium（Playwright 自带） | — | 同上 | 装完 playwright 后还要跑 `python -m playwright install chromium`，否则启动浏览器会报错 |
| `imageio-ffmpeg` | 0.6.0 | tts.py、sfx.py、render.py、concat.py、bgm.py | 自带一个 ffmpeg 可执行文件，**不需要另装 ffmpeg**，也不用配 PATH |
| `numpy` | 2.4.3 | sfx.py、bgm.py、library/transition/transition.py | 音频运算 |
| `scipy` | 1.18.0 | sfx.py、bgm.py、library/transition/transition.py | 滤波、混响卷积、重采样 |

其余用到的（`json`、`wave`、`subprocess`、`asyncio`、`concurrent.futures` 等）都是 Python 标准库。

### 其他要求
- **字体**：Segoe UI 和 Microsoft YaHei，Windows 自带；换到 Mac / Linux 要手动装，否则字形和宽度会变，`check_layout.py` 的结果也会不同
- **联网**：配音要连微软 edge-tts 服务；`library/tts_cache/` 里已有的句子不需要联网。请求太频繁时服务会返回 429，等一会儿再跑
- **硬件**：`render.py --workers 8` 会开 8 个浏览器，建议 8 核以上、16GB 内存；机器弱就把 `--workers` 调小

### 可选：L0 的 kokoro 本地配音试验
只有跑 `videos/L0/experiments/kokoro/build.py` 时才需要，主流程用不到（目前本机没装）：
```
pip install kokoro-onnx onnxruntime soundfile
```

## 8. 从零生成一个视频的成片
```
# 每一段：intro（不带 --section）、ch1、ch2 …（按该视频 video.json 的 order）
python tts.py --video L0 --section ch1
python check_subs.py --video L0 --section ch1
python sfx.py --video L0 --section ch1
python check_layout.py --video L0 --section ch1
python render.py --video L0 --section ch1 --preview 3,12     # 看一眼
python render.py --video L0 --section ch1 --workers 8

# 所有段落做完后
python concat.py --video L0 --check
python bgm.py --video L0 --full --track "library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3"
```
