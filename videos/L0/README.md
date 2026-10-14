# L0 — Knowledge Powers AI: Understanding Knowledge Management at Lenovo

本项目的第一个视频。制作规范见根目录 [CLAUDE.md](../../CLAUDE.md)（所有视频共用），改动记录见 [change_log.md](change_log.md)。

## 概况
| 项目 | 内容 |
|---|---|
| 讲解稿 | "Knowledge Powers AI: Understanding Knowledge Management at Lenovo" |
| 状态 | 已完成 |
| 成片 | `output/full.mp4`，5:32.5，1920×1080 / 30fps |
| 时长上限 | ≤ 9:00（`video.json` 没写 `limit_seconds`，用默认值） |
| 顶部章节标签 | `KNOWLEDGE MANAGEMENT`（写死在 `engine/engine.js` 的 `injectChrome` 和 `source/slides/intro.html` 里） |
| 配音 | edge-tts `en-US-AriaNeural`，语速 -4% |
| 背景音乐 | `library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3`，副歌落在 Closing 收尾页 |
| 章节转场声 | `library/transition/orig_low_v1.wav` |
| 中英旁白对照 | [narration_script.md](narration_script.md)：手工整理，旁白或时长变了要手动更新 |

## 段落顺序（`video.json`）
| id | 时长 | 页面 |
|---|---|---|
| `intro` | 67.9s | 封面 Lenovo EKM → Knowledge We Create Every Day → Knowledge Is Everywhere → KM Serves Both Employees and AI |
| `ch1` | 60.4s | CHAPTER 1 What is Knowledge Management? → Knowledge Management (KM) → What KM Ensures → Shared, Not Isolated → A Strategic Enterprise Asset |
| `ch2` | 29.5s | CHAPTER 2 What Knowledge Management Means at Lenovo → More Than a Process → An AI-Ready Ecosystem |
| `ch3` | 76.0s | CHAPTER 3 Why KM Matters to Every Employee → Without KM vs. With KM → Every Employee Plays a Role → From Individual to Enterprise |
| `ch4` | 59.2s | CHAPTER 4 Lenovo EKM Framework → Knowledge as a Strategic Asset → Three Change Pillars → A Foundation That Scales |
| `closing` | 39.5s | CLOSING Powering AI at Lenovo → A More Connected Organization → A Strategic Advantage → Powers AI Innovation |

## 生成成片
```
python concat.py --check
python bgm.py --full --track "library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3"
```
（在根目录运行，`--video` 默认就是 L0。）

## 只属于 L0 的情况
- **ch5 已停用**（2026-10-14）：不在 `video.json` 里，`output/ch5.mp4` 已删。文稿、页面、时间轴、配音作为素材保留，需要时 `--section ch5` 可以重建。它的 "A More Connected Organization" 页已经复制到 Closing
- **配音缓存有缺口**：ch1 第 3–8 句、ch3 第 4–22 句是配音缓存出现之前合成的，`library/tts_cache/` 里没有。现有的配音和时间轴是完整的；但重跑 `tts.py --section ch1 / ch3` 会联网重新合成，声音可能有细微差别，之后要重新检查画面时间
- **v2 / v3 背景音乐**：成片 `full_v2.mp4` / `full_v3.mp4` 已删，素材留在 `build/bgm/`（`bgm_full_v2/v3.wav`、`full_v2/v3_bgm_mix.wav`、`preview_v2_*` / `preview_v3_*`）。要重新出片用 `bgm.py --full --tag v2` / `--style remix --tag v3`
- **intro.html 自带一份内联引擎**，不引用 `engine/engine.js`，改引擎时要同步考虑它
- **用户指定的用词例外**（画面文字不完全用旁白原词）：见 change_log 里 Ch4 EKM 房子、Ch4 S2 "People" 两条

## 其他文件
| 位置 | 内容 |
|---|---|
| `output/trials/bac_closing.mp4`、`bac2_closing.mp4` | 早期 Closing 单段配乐试验（合成配乐 / morrix 曲目），对应音频在 `build/bgm/bgm*_closing.wav`、`closing_bgm*_mix.wav` |
| `backup/intro_v1/` | 2026-10-10 重做前的 Intro（旧版文件结构，原样保存，不能直接用现在的脚本跑） |
| `backup/closing_v1/` | 删页前的 Closing |
| `experiments/kokoro/` | 用本地 Kokoro TTS 给 Closing 重新配音的独立试验（`build.py`），读 L0 的 source / build（只读），输出全在 `experiments/kokoro/` 里。Closing 文稿在这之后改过，要重新跑它的 tts 步骤 |
