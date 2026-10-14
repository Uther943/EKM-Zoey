# Trainning — From Code to Video

讲"视频是怎么用代码做出来的"，语气通俗，面向第一次接触本项目的人。制作规范见根目录 [CLAUDE.md](../../CLAUDE.md)（所有视频共用），改动记录见 [change_log.md](change_log.md)。

## 概况
| 项目 | 内容 |
|---|---|
| 封面 | **From Code to Video** / How a Script Becomes an Explainer Video |
| 讲解稿 | Claude 起草，用户确认（参考根目录 README 第 1 节） |
| 状态 | 已完成，成片 `output/full.mp4`，2:10.3，1920×1080 / 30fps |
| 时长上限 | ≤ 3:00（`video.json` 的 `limit_seconds` = 180） |
| 分章 | 分章：intro + ch1–ch3 + closing |
| 顶部章节标签 | `KNOWLEDGE MANAGEMENT`（沿用 L0，引擎不改） |
| Logo | 联想 `engine/assets/lenovo.png` |
| 配音 | edge-tts `en-US-GuyNeural`（男声），语速 -4% |
| 背景音乐 | `library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3`，副歌落在 Closing 收尾页 S3 |
| 音效 | Intro 开场音效、章节转场声 `library/transition/orig_low_v1.wav`；"叮"3 处：ch2 网络长出、ch3 视频核心长出、Closing 收尾核心长出（文稿 `sfx`） |

## 段落顺序（`video.json`）
| id | 时长 | 页面 |
|---|---|---|
| `intro` | 24.4s | 封面 From Code to Video → Built with Code → Five Simple Steps |
| `ch1` | 24.5s | CHAPTER 1 Each Section Is a Web Page → Just Like a Slide → Same Time, Same Picture |
| `ch2` | 25.4s | CHAPTER 2 The Voice Sets the Clock → When Each Word Is Spoken → Tied to a Word |
| `ch3` | 27.4s | CHAPTER 3 Pictures Become a Video → A Screenshot at Every Step → One Track Under the Whole Film |
| `closing` | 28.5s | CLOSING Written, Told, and Built → Just Edit the Script → Code Checks the Layout → Written, Told, and Built（收尾页） |

## 生成成片
```
python concat.py --video Trainning --check
python bgm.py --video Trainning --full --track "library/music/morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750.mp3"
```
