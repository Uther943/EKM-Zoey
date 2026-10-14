# 项目级变更记录（change log）

> 记录所有视频共用部分的改动：流水线代码（`*.py`）、`engine/`、`library/`、目录结构、`CLAUDE.md` 规范。**先在这里登记，再执行。**
> 某个视频的内容改动记在 `videos/<视频>/change_log.md`。

| 日期 | 范围 | 改动 |
|---|---|---|
| 2026-10-14 | 目录结构 / 代码 / 文档 | **项目改成多视频结构**，现有全部内容归为 L0（L0 日志同日有一条对应记录）。① 目录：`videos/L0/{source,build,output}` + `backup/`、`experiments/kokoro/`；共用的 `engine/`（原 `slides/engine.*`、`slides/assets/`）、`library/music/`（原 `background sound/` 里的原曲）、`library/transition/`（原 `transition sound/`）、`library/tts_cache/`（原 `audio/tts_cache/`）。② Intro 统一命名为 `intro`（`scripts/intro.json`、`slides/intro.html`、`timelines/intro.json` + `timeline_intro.js`、`audio/units/intro/`、预览帧 `intro_<t>.png`）。③ 代码：`sections.paths(section, video)` 给出全部路径（新增 `sfx` / `bgm` / `preview` / `seg` / `output` / `trials`）；`order(video)` 读 `videos/<v>/video.json` 替代 `ORDER`；所有脚本加 `--video`（默认 L0）；`bgm.py` 的单段试验片改到 `output/trials/`；`engine.js` 的 Logo 按 `engine.js` 自身位置取；页面改为相对路径引用 `engine/` 和 `build/timelines/`；`transition.py`、kokoro 试验跟着改路径。④ 文档：`CLAUDE.md` 改为全项目通用规范（新增第 16 节项目结构），L0 专属内容移到 `videos/L0/README.md`；`README.md` 按新结构重写。⑤ 验证：重新生成的 L0 时间轴、各段混音、成片混音与搬迁前逐字节一致，10 张抽样帧逐像素一致，6 段版面检查全部通过，成片 5:32.5 不变 |
| 2026-10-14 | 文档 | `README.md` 最前面新增「第 0 节 新视频开工：先问清楚再动手」：开工前要问哪些问题（分两轮，每题给选项、默认项排第一）、每项的默认值（分章结构、背景音乐、转场声、配音、字幕、时长上限、顶部标签、Logo）、回答记到哪里，以及从开工到成片的逐步流程和每步的确认点；`CLAUDE.md` 第 16 节"新建视频"一条加上"先按 README 第 0 节提问"。只改文档，不改代码 |
| 2026-10-14 | 代码 / 文档 | 新建视频 **Trainning**（"From Code to Video"，内容见 `videos/Trainning/change_log.md`）。① `sections.py` 加 `limit(video)`：读 `video.json` 里可选的 `limit_seconds`，没有就是 9:00；`concat.py` 的时长上限改用它（L0 不写，仍是 9:00）。② 根目录 `README.md` 的视频表加 Trainning 一行 |
