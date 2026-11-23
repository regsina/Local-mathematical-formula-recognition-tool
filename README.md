# 本地数学公式识别工具

将单个数学公式的截图、图片或鼠标手写笔迹在本机识别为可编辑 LaTeX，支持校对、预览、本地历史，并复制到 WPS 使用。需求定义见 `开发需求/PRD.md`（v0.5）。

## 当前状态

框架+接口阶段（对应 PRD 门禁：G1 技术基线冻结前仅开发通用界面与框架能力）：

- 已实现：截图框选、图片导入（EXIF/Unicode/超限处理）、鼠标画板、任务状态机（单任务/取消/迟到结果丢弃）、LaTeX 编辑与本地预览、历史记录（原子写入/损坏隔离/单条删除）、自动保存（1 秒防抖）、首次运行环境检查、多公式输入固定提示。
- 识别模型当前为**占位识别器**（`src/recognizer/placeholder.py`），仅用于流程验证，不代表首版识别质量。UniMERNet 将在 G1 冻结后接入 `src/recognizer/` 接口。
- 预览使用 matplotlib mathtext，仅支持其语法子集；不支持的首版语法按 PRD 6.3 走“渲染失败保留源码”路径。最终语法子集见 G1 待冻结的《LaTeX 命令及 WPS 兼容表》。

## 环境要求

- Windows 10/11，Python 3.10+
- 目标设备：NVIDIA 显卡（验收设备 5060、8GB 显存）

## 安装与运行

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe run.py
```

依赖安装于项目内虚拟环境 `.venv`（已加入 .gitignore），不污染全局 Python。首次运行会执行环境检查（系统、Python、显卡驱动、磁盘空间），通过后进入主界面；准备完成后全程离线。

## 冒烟测试

```bash
.venv/Scripts/python.exe tests/smoke_test.py
```

覆盖：历史存储（创建/更新/原子写入/损坏隔离/删除）、渲染（正常/非法/超长/空白）、任务状态机（成功/取消/迟到结果丢弃）、主窗口端到端（识别→建记录→自动保存）。

## 目录结构

```
run.py                  入口
src/
  app.py                应用装配与首次运行引导
  config.py             拟定阈值集中管理（G1 冻结项已标注）
  main_window.py        主窗口与核心交互
  task_manager.py       任务状态机（taskId/单任务/取消中）
  renderer.py           mathtext 渲染（超时与长度上限）
  history_store.py      历史记录原子存储
  history_panel.py      历史列表与删除确认
  input_screenshot.py   截图框选覆盖层
  input_canvas.py       鼠标画板（笔/橡皮/撤销/清空）
  editor_preview.py     源码编辑器（防抖）与预览面板
  env_check.py          环境检查
  first_run_dialog.py   首次运行向导
  recognizer/           识别器接口与实现（placeholder，G1 接入 UniMERNet）
tests/smoke_test.py     冒烟测试
```

## 数据位置

历史记录与模型缓存统一存放于 `%APPDATA%/LocalFormulaRecognition/`，不写入原始图片所在目录；卸载不删除用户数据（PRD 7.4）。