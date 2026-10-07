"""Сборка вертикального ролика 1080x1920 из картинок и подписей через ffmpeg."""

import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def find_font(path=None):
    for candidate in [path, os.environ.get("AUTOPOST_FONT"), *FONT_CANDIDATES]:
        if candidate and os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("Не найден шрифт с кириллицей, укажите --font или AUTOPOST_FONT")


def placeholder_image(out_path, index, label):
    """Градиентная заглушка, если Gemini недоступен."""
    palettes = [((255, 94, 98), (255, 195, 113)), ((54, 209, 220), (91, 134, 229)),
                ((142, 45, 226), (74, 0, 224)), ((17, 153, 142), (56, 239, 125))]
    top, bottom = palettes[index % len(palettes)]
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        draw.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    font = ImageFont.truetype(find_font(), 64)
    draw.text((W // 2, H // 3), label, font=font, fill=(255, 255, 255), anchor="mm")
    img.save(out_path)
    return out_path


def cover_fit(src, out_path):
    """Обрезает картинку под 9:16 и масштабирует до 1080x1920."""
    img = Image.open(src).convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img.crop((left, top, left + W, top + H)).save(out_path)
    return out_path


def _wrap(text, font, draw, max_width):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def caption_overlay(text, out_path, font_path=None, size=72):
    """Прозрачный PNG с текстом на полупрозрачной плашке в нижней трети кадра."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(find_font(font_path), size)
    lines = _wrap(text or "", font, draw, W - 200)
    if not lines:
        img.save(out_path)
        return out_path
    line_h = int(size * 1.25)
    pad = 40
    box_h = line_h * len(lines) + pad * 2
    box_w = max(draw.textlength(l, font=font) for l in lines) + pad * 2
    y0 = int(H * 0.68) - box_h // 2
    x0 = (W - box_w) // 2
    draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=36, fill=(0, 0, 0, 150))
    for i, line in enumerate(lines):
        draw.text((W // 2, y0 + pad + line_h * i + line_h // 2), line, font=font,
                  fill=(255, 255, 255, 255), anchor="mm")
    img.save(out_path)
    return out_path


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg завершился с ошибкой:\n{result.stderr[-2000:]}")


def render_scene(image, overlay, duration, out_path, zoom_in=True):
    """Один клип: медленный зум (Ken Burns) + появление подписи."""
    frames = int(duration * FPS)
    zoom = f"1+0.12*on/{frames}" if zoom_in else f"1.12-0.12*on/{frames}"
    vf = (
        f"[0:v]scale={W * 2}:{H * 2},"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        f"setsar=1[bg];"
        f"[1:v]format=rgba,fade=t=in:st=0.3:d=0.5:alpha=1[txt];"
        f"[bg][txt]overlay=0:0:shortest=1,format=yuv420p[v]"
    )
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", image, "-loop", "1", "-t", str(duration), "-i", overlay,
        "-filter_complex", vf, "-map", "[v]", "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), out_path,
    ])
    return out_path


def concat_with_transitions(clips, durations, out_path, music=None, transition=0.5):
    """Склеивает клипы через xfade и добавляет звук (музыку или тишину)."""
    inputs = []
    for clip in clips:
        inputs += ["-i", clip]
    total = sum(durations) - transition * (len(clips) - 1)

    if len(clips) == 1:
        vf, vlabel = "[0:v]null[v]", "[v]"
    else:
        steps, prev, offset = [], "[0:v]", 0.0
        for i in range(1, len(clips)):
            offset += durations[i - 1] - transition
            label = f"[x{i}]"
            steps.append(f"{prev}[{i}:v]xfade=transition=fade:duration={transition}:offset={offset:.3f}{label}")
            prev = label
        vf, vlabel = ";".join(steps), prev

    audio_idx = len(clips)
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        af = f"[{audio_idx}:a]atrim=0:{total:.3f},afade=t=out:st={max(total - 1, 0):.3f}:d=1[a]"
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        af = f"[{audio_idx}:a]atrim=0:{total:.3f}[a]"

    # Параметры под требования Instagram Reels: H.264, yuv420p, 30 fps, AAC 48 кГц, moov в начале.
    _run([
        "ffmpeg", "-y", "-loglevel", "error", *inputs,
        "-filter_complex", f"{vf};{af}", "-map", vlabel, "-map", "[a]",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", "-t", f"{total:.3f}", out_path,
    ])
    return out_path
