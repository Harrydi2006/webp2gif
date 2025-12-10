# Batch convert animated WebP images to GIF
# Usage examples:
#   python convert_webp2gif.py -i ./input -o ./output --overwrite
#   python convert_webp2gif.py -i . -o ./gif_out --include-static -v

import argparse
import logging
from pathlib import Path
from PIL import Image, ImageSequence
import shutil
import concurrent.futures
import os


def is_animated(img: Image.Image) -> bool:
    try:
        return getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1
    except Exception:
        return False

# 解析颜色字符串（#RRGGBB 或 R,G,B）
def parse_color(s: str):
    try:
        s = s.strip()
        if s.startswith('#') and len(s) == 7:
            return tuple(int(s[i:i+2], 16) for i in (1, 3, 5))
        parts = s.split(',')
        if len(parts) == 3:
            rgb = tuple(max(0, min(255, int(p.strip()))) for p in parts)
            return rgb
    except Exception:
        pass
    return (255, 255, 255)


def convert_file(src_path: Path, dst_path: Path, skip_static: bool = True, transparent_gif: bool = False, matte_color=(255, 255, 255), alpha_threshold: int = 0, no_optimize: bool = False, no_dither: bool = False) -> bool:
    try:
        with Image.open(src_path) as im:
            animated = is_animated(im)
            if not animated and skip_static:
                logging.info(f"跳过静态图片: {src_path.name}")
                return False

            frames = []
            durations = []

            transparency_index = None
            base_palette_img = None
            base_palette = None

            # 抖动模式（0: 无抖动，1: Floyd-Steinberg）
            dither_mode = 0 if no_dither else 1

            for idx, frame in enumerate(ImageSequence.Iterator(im)):
                # 帧时长（毫秒），缺省给一个合理值
                duration = frame.info.get("duration", im.info.get("duration", 100))
                if not isinstance(duration, int) or duration <= 0:
                    duration = 100
                durations.append(duration)

                frame_rgba = frame.convert("RGBA")

                if transparent_gif:
                    # 将非透明像素合成到哑光背景；严格映射 alpha≤阈值 的像素为透明
                    matte_bg = Image.new("RGB", frame_rgba.size, matte_color)
                    alpha = frame_rgba.split()[-1]
                    rgb = frame_rgba.convert("RGB")
                    composed = matte_bg.copy()
                    composed.paste(rgb, mask=alpha)

                    if idx == 0:
                        # 首帧用 255 色生成自适应调色板，保留一个索引用于透明
                        frame_q = composed.convert("P", palette=Image.ADAPTIVE, colors=255, dither=dither_mode)
                        pal = frame_q.getpalette()
                        # 预留最后一个索引作为透明色（调色板颜色本身不会显示，因为设为 transparency）
                        if len(pal) < 256 * 3:
                            pal += [0] * (256 * 3 - len(pal))
                        pal[3*255:3*256] = list(matte_color)
                        base_palette_img = Image.new("P", (1, 1))
                        base_palette_img.putpalette(pal)
                        base_palette = pal
                        transparency_index = 255

                        # 使用掩膜快速设置透明索引，避免逐像素 Python 循环
                        frame_p = frame_q.copy()
                        frame_p.putpalette(base_palette)
                        mask = alpha.point(lambda a: 255 if a <= alpha_threshold else 0)
                        frame_p.paste(transparency_index, mask=mask)
                    else:
                        # 后续帧使用同一调色板进行量化
                        frame_q = composed.quantize(palette=base_palette_img, dither=dither_mode)
                        frame_p = frame_q.copy()
                        frame_p.putpalette(base_palette)
                        mask = alpha.point(lambda a: 255 if a <= alpha_threshold else 0)
                        frame_p.paste(transparency_index, mask=mask)

                    frames.append(frame_p)
                else:
                    # 将透明背景合成到白色，避免GIF出现黑边/黑底；量化时按需控制抖动
                    white_bg = Image.new("RGBA", frame_rgba.size, (255, 255, 255, 255))
                    composed = Image.alpha_composite(white_bg, frame_rgba)
                    # 自适应调色板以减小GIF体积
                    frame_p = composed.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=256, dither=dither_mode)
                    frames.append(frame_p)

            # 保存为GIF动图
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            save_kwargs = dict(
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,              # 0表示无限循环
                optimize=(not no_optimize),
                disposal=2,          # 每帧绘制前恢复到背景，减少残影
            )
            if transparent_gif and transparency_index is not None:
                save_kwargs["transparency"] = transparency_index

            frames[0].save(dst_path, **save_kwargs)
            logging.info(f"转换成功: {src_path.name} -> {dst_path.name}")
            return True
    except Exception as e:
        logging.error(f"转换失败: {src_path}，错误: {e}")
        return False


def export_png_frames(src_path: Path, out_base_dir: Path, overwrite: bool = False, include_static: bool = False, input_root: Path | None = None, preserve_structure: bool = False, inplace: bool = False) -> bool:
    try:
        with Image.open(src_path) as im:
            animated = is_animated(im)
            if not animated and not include_static:
                logging.info(f"跳过静态图片PNG导出: {src_path.name}")
                return False

            # 计算输出目录
            if inplace:
                target_dir = src_path.parent / src_path.stem
            else:
                if preserve_structure and input_root is not None:
                    rel = src_path.relative_to(input_root)
                    target_dir = out_base_dir / rel.parent / src_path.stem
                else:
                    target_dir = out_base_dir / src_path.stem

            if target_dir.exists():
                if not overwrite:
                    logging.info(f"PNG帧目录已存在，跳过: {target_dir}")
                    return False
                # 覆盖模式下清理旧目录
                try:
                    shutil.rmtree(target_dir)
                except Exception:
                    pass
            target_dir.mkdir(parents=True, exist_ok=True)

            count = 0
            for idx, frame in enumerate(ImageSequence.Iterator(im)):
                frame_rgba = frame.convert("RGBA")
                save_path = target_dir / f"{idx:04d}.png"
                frame_rgba.save(save_path, format="PNG")
                count += 1

            # 如果是静态且 include_static，则也导出一帧
            if count == 0 and include_static:
                frame_rgba = im.convert("RGBA")
                save_path = target_dir / "0000.png"
                frame_rgba.save(save_path, format="PNG")
                count = 1

            logging.info(f"PNG帧导出成功: {src_path.name} -> {target_dir} (共 {count} 帧)")
            return True
    except Exception as e:
        logging.error(f"PNG帧导出失败: {src_path}，错误: {e}")
        return False


def batch_export_png(input_dir: Path, output_dir: Path, overwrite: bool = False, include_static: bool = False, recursive: bool = False, workers: int = 4, preserve_structure: bool = False, inplace: bool = False):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.exists():
        logging.error(f"输入目录不存在: {input_dir}")
        return

    if not inplace:
        output_dir.mkdir(parents=True, exist_ok=True)

    files_iter = input_dir.rglob("*.webp") if recursive else input_dir.glob("*.webp")
    files = sorted(list(files_iter))

    total = len(files)
    exported = 0
    skipped = 0

    def _task(f):
        return export_png_frames(f, output_dir, overwrite=overwrite, include_static=include_static, input_root=input_dir, preserve_structure=preserve_structure, inplace=inplace)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = [ex.submit(_task, f) for f in files]
        for fut in concurrent.futures.as_completed(futures):
            ok = False
            try:
                ok = fut.result()
            except Exception as e:
                logging.error(f"PNG帧导出任务出错: {e}")
            if ok:
                exported += 1
            else:
                skipped += 1

    logging.info(f"PNG导出完成。总计: {total}，已导出: {exported}，已跳过: {skipped}")


def _convert_task(args):
    # 可被进程池pickle的顶层函数包装
    f, out_path, skip_static, transparent_gif, matte_color, alpha_threshold, no_optimize, no_dither = args
    return convert_file(f, out_path, skip_static=skip_static, transparent_gif=transparent_gif, matte_color=matte_color, alpha_threshold=alpha_threshold, no_optimize=no_optimize, no_dither=no_dither)


def batch_convert(input_dir: Path, output_dir: Path, overwrite: bool = False, skip_static: bool = True, recursive: bool = False, workers: int = 4, transparent_gif: bool = False, matte_color=(255, 255, 255), preserve_structure: bool = False, inplace: bool = False, alpha_threshold: int = 0, no_optimize: bool = False, no_dither: bool = False, use_processes: bool = False):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.exists():
        logging.error(f"输入目录不存在: {input_dir}")
        return

    if not inplace:
        output_dir.mkdir(parents=True, exist_ok=True)

    files_iter = input_dir.rglob("*.webp") if recursive else input_dir.glob("*.webp")
    files = sorted(list(files_iter))

    total = len(files)
    converted = 0
    skipped = 0

    tasks = []
    for f in files:
        # 计算输出文件路径
        if inplace:
            out_path = f.parent / (f.stem + ".gif")
        else:
            if preserve_structure:
                rel = f.relative_to(input_dir)
                out_path = output_dir / rel.parent / (f.stem + ".gif")
            else:
                out_path = output_dir / (f.stem + ".gif")

        if out_path.exists() and not overwrite:
            logging.info(f"已存在，跳过: {out_path}")
            skipped += 1
            continue
        tasks.append((f, out_path, skip_static, transparent_gif, matte_color, alpha_threshold, no_optimize, no_dither))

    # 根据开关选择线程池或进程池，以提升多核利用率
    Executor = concurrent.futures.ProcessPoolExecutor if use_processes else concurrent.futures.ThreadPoolExecutor
    with Executor(max_workers=max(1, workers)) as ex:
        if use_processes:
            futures = [ex.submit(_convert_task, t) for t in tasks]
        else:
            futures = [ex.submit(lambda a: convert_file(a[0], a[1], skip_static=a[2], transparent_gif=a[3], matte_color=a[4], alpha_threshold=a[5], no_optimize=a[6], no_dither=a[7]), t) for t in tasks]
        for fut in concurrent.futures.as_completed(futures):
            ok = False
            try:
                ok = fut.result()
            except Exception as e:
                logging.error(f"GIF转换任务出错: {e}")
            if ok:
                converted += 1
            else:
                skipped += 1

    logging.info(f"完成。总计: {total}，已转换: {converted}，已跳过: {skipped}")



def main():
    parser = argparse.ArgumentParser(description="批量将WebP动图转换为GIF，或导出透明PNG帧序列")
    parser.add_argument("-i", "--input", default=".", help="输入目录（包含.webp文件）")
    parser.add_argument("-o", "--output", default="output_gif", help="GIF输出目录（保存.gif文件）")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的输出（GIF或PNG帧）")
    parser.add_argument("--include-static", action="store_true", help="同时处理静态WebP（GIF或PNG帧）")
    parser.add_argument("--export-png-frames", action="store_true", help="将每个WebP导出为透明背景的PNG帧序列")
    parser.add_argument("--png-output", default="output_png_frames", help="PNG帧输出目录（每个WebP一个子目录）")
    parser.add_argument("--recursive", action="store_true", help="递归遍历子目录中的 .webp 文件")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) // 2), help="并行工作线程数（默认CPU核数的一半）")
    parser.add_argument("--transparent-gif", action="store_true", help="输出PowerPoint兼容的透明背景GIF（单色透明）")
    parser.add_argument("--matte", default="#FFFFFF", help="透明GIF的哑光背景色（#RRGGBB或R,G,B），匹配PPT背景可减少光晕")
    parser.add_argument("--preserve-structure", action="store_true", help="在输出根目录下保留与输入相同的子目录结构")
    parser.add_argument("--gif-inplace", action="store_true", help="GIF输出到原始文件所在目录")
    parser.add_argument("--png-inplace", action="store_true", help="PNG帧输出到原始文件所在目录（每个文件生成同名子目录）")
    parser.add_argument("--alpha-threshold", type=int, default=0, help="将 alpha≤阈值 的像素视为透明（0 表示仅完全透明像素透明）")
    parser.add_argument("--no-optimize", action="store_true", help="禁用GIF优化以加快保存速度")
    parser.add_argument("--no-dither", action="store_true", help="禁用抖动以加快量化速度并减少GIL影响")
    parser.add_argument("--use-processes", action="store_true", help="使用进程并行（更好利用多核），适合大量文件转换")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示更详细的日志")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    matte_color = parse_color(args.matte)

    # GIF 转换（支持多线程/递归/透明GIF/结构保持/原地输出/严格透明映射）
    batch_convert(
        Path(args.input), Path(args.output), overwrite=args.overwrite, skip_static=not args.include_static,
        recursive=args.recursive, workers=args.workers, transparent_gif=args.transparent_gif, matte_color=matte_color,
        preserve_structure=args.preserve_structure, inplace=args.gif_inplace, alpha_threshold=max(0, min(255, args.alpha_threshold)), no_optimize=args.no_optimize, no_dither=args.no_dither, use_processes=args.use_processes
    )

    # PNG 帧导出（可选，支持多线程/递归/结构保持/原地输出）
    if args.export_png_frames:
        batch_export_png(
            Path(args.input), Path(args.png_output), overwrite=args.overwrite, include_static=args.include_static,
            recursive=args.recursive, workers=args.workers, preserve_structure=args.preserve_structure, inplace=args.png_inplace
        )


if __name__ == "__main__":
    main()