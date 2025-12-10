# webp2gif 使用说明 | WebP to GIF Converter

仓库：https://github.com/Harrydi2006/webp2gif

## 简介 | Overview
- 一个基于 Pillow 的 Python 脚本，批量将 WebP（含透明与动图）转换为 GIF，或导出透明 PNG 帧。| A Python script using Pillow to batch-convert WebP (with alpha/animation) to GIF, or export transparent PNG frames.
- 支持严格透明映射、并行加速、目录结构保留、抖动与优化控制。| Supports strict alpha-to-GIF transparency mapping, parallelism, directory structure preservation, and dithering/optimization controls.

## 特性 | Features
- 递归批量转换 .webp | Recursive batch conversion of .webp
- 透明 GIF（单色索引透明）与严格 alpha 阈值 | Transparent GIF (indexed single-color) with strict alpha threshold
- 导出透明 PNG 帧序列 | Export transparent PNG frames
- 线程或进程并行 | Thread or process parallelism
- 抖动与优化开关 | Dithering and optimize toggles

## 环境与安装 | Requirements & Installation
- Python 3.9+（建议虚拟环境）| Python 3.9+ (virtual env recommended)
- 安装依赖 | Install deps:
  - 创建并激活虚拟环境（可选）| Create/activate venv (optional):
    - `python -m venv .venv`
    - `./.venv/Scripts/Activate.ps1`
  - 安装 | Install: `pip install -r requirements.txt`

## 快速开始 | Quick Start
- 输出到 gif_out，启用透明 GIF（alpha-threshold=0，白色哑光），保留目录结构，24 进程并行：| Output to gif_out, transparent GIF (alpha-threshold=0, white matte), preserve structure, 24 processes:
```
./.venv/Scripts/python.exe convert_webp2gif.py \
  -i "C:\\Users\\Harrydi2006\\Downloads\\Compressed\\Telegram-Animated-Emojis-main\\Telegram-Animated-Emojis-main" \
  -o "gif_out" \
  --transparent-gif --alpha-threshold 0 --matte "#FFFFFF" \
  --recursive --overwrite --preserve-structure \
  --workers 24 --use-processes
```
- 就地输出（写回原目录）| In-place output:
```
./.venv/Scripts/python.exe convert_webp2gif.py -i "<source>" --gif-inplace \
  --transparent-gif --alpha-threshold 0 --matte "#FFFFFF" --recursive --overwrite
```
- 导出透明 PNG 帧 | Export transparent PNG frames:
```
./.venv/Scripts/python.exe convert_webp2gif.py -i "<source>" \
  --export-png-frames --png-output "output_png_frames" --recursive --overwrite
```

## 常见用法 | Common Usage
- 启用抖动与优化（默认）：不传 `--no-dither`、`--no-optimize`。| Enable dithering & optimize (default): do not pass `--no-dither`, `--no-optimize`.
- 关闭抖动与优化（更快，边缘更干净）：| Disable for speed & cleaner edges:
```
... --no-dither --no-optimize
```
- 深色背景适配：`--matte "#000000"`。| Dark matte: `--matte "#000000"`.
- 半透明视为透明：`--alpha-threshold 10`/`20`。| Treat faint alpha as transparent.

## 参数摘要 | Arguments (summary)
- `-i, --input` 输入目录 | Input dir
- `-o, --output` 输出根目录 | Output root
- `--overwrite` 覆盖输出 | Overwrite
- `--include-static` 处理静态 WebP | Include static WebP
- `--export-png-frames` 导出 PNG 帧 | Export PNG frames
- `--png-output` PNG 输出根目录 | PNG output root
- `--recursive` 递归 | Recursive
- `--workers` 并行数量 | Parallel workers
- `--transparent-gif` 透明 GIF | Transparent GIF
- `--matte` 哑光色（#RRGGBB 或 R,G,B）| Matte color (#RRGGBB or R,G,B)
- `--preserve-structure` 保留目录结构 | Preserve structure
- `--gif-inplace` GIF 写回原目录 | GIF inplace
- `--png-inplace` PNG 帧写回原目录 | PNG inplace
- `--alpha-threshold` alpha≤阈值 视为透明 | alpha≤threshold as transparent
- `--no-optimize` 禁用 GIF 优化 | Disable GIF optimize
- `--no-dither` 禁用抖动 | Disable dithering
- `--use-processes` 使用进程并行 | Use processes
- `-v, --verbose` 详细日志 | Verbose logs

## 透明与抖动 | Transparency & Dithering
- 严格透明：按阈值将像素映射为 GIF 透明索引，避免误透明。| Strict alpha-to-index mapping avoids unintended transparency.
- 抖动：用细微噪点缓解渐变条带；图标/文字建议关闭以保持边缘干净。| Dithering reduces banding; disable for icons/text to keep edges clean.
- 优化：GIF 保存的压缩/帧差优化；默认开启，批量时可临时关闭加速。| Optimize is enabled by default; can be disabled for speed.

## 性能建议 | Performance Tips
- 大量文件：`--use-processes`，`--workers≈CPU 核心数`。| For large sets, use processes with workers≈CPU cores.
- 首次快速生成可关闭抖动/优化，最终版再开启优化。| Disable for drafts, enable for final.
