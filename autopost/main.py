"""Собрать вертикальный ролик и (по желанию) опубликовать его в Instagram Reels.

Примеры:
    python -m autopost.main --topic "Футболки с принтами от нейросети" --publish
    python -m autopost.main --scenario autopost/examples/scenario.json --offline
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime

from . import gemini, render


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


def build_video(scenario, out_path, offline=False, music=None, font=None, scene_duration=3.5, log=print):
    scenes = scenario["scenes"]
    with tempfile.TemporaryDirectory(prefix="autopost-") as tmp:
        clips, durations = [], []
        for i, scene in enumerate(scenes):
            raw = os.path.join(tmp, f"raw_{i}.png")
            if scene.get("image") and os.path.exists(scene["image"]):
                raw = scene["image"]
            elif offline:
                render.placeholder_image(raw, i, f"Сцена {i + 1}")
            else:
                log(f"[{i + 1}/{len(scenes)}] Генерирую картинку в Gemini…")
                try:
                    gemini.generate_image(scene["image_prompt"], raw)
                except gemini.GeminiError as e:
                    log(f"  не получилось ({e}), ставлю заглушку")
                    render.placeholder_image(raw, i, f"Сцена {i + 1}")

            bg = render.cover_fit(raw, os.path.join(tmp, f"bg_{i}.png"))
            overlay = render.caption_overlay(scene.get("text", ""), os.path.join(tmp, f"txt_{i}.png"), font)
            duration = float(scene.get("duration", scene_duration))
            log(f"[{i + 1}/{len(scenes)}] Рендерю сцену ({duration} с)")
            clips.append(render.render_scene(bg, overlay, duration, os.path.join(tmp, f"clip_{i}.mp4"),
                                             zoom_in=i % 2 == 0))
            durations.append(duration)

        log("Склеиваю ролик…")
        render.concat_with_transitions(clips, durations, out_path, music=music)
    return out_path


def main(argv=None):
    load_env()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic", help="тема ролика: сценарий напишет Gemini")
    src.add_argument("--scenario", help="готовый сценарий в JSON (см. examples/scenario.json)")
    p.add_argument("--scenes", type=int, default=4, help="сколько сцен просить у Gemini")
    p.add_argument("--out", help="куда сохранить mp4 (по умолчанию output/reel_<время>.mp4)")
    p.add_argument("--music", help="mp3/m4a для фона; без него будет тихая дорожка")
    p.add_argument("--font", help="TTF-шрифт с кириллицей")
    p.add_argument("--duration", type=float, default=3.5, help="длительность сцены, с")
    p.add_argument("--offline", action="store_true", help="не ходить в Gemini, вместо картинок заглушки")
    p.add_argument("--publish", action="store_true", help="опубликовать в Instagram Reels")
    p.add_argument("--video-url", help="публичная ссылка на mp4 вместо загрузки файла")
    args = p.parse_args(argv)

    if args.scenario:
        with open(args.scenario, encoding="utf-8") as f:
            scenario = json.load(f)
    else:
        if args.offline:
            p.error("--topic требует Gemini, уберите --offline или передайте --scenario")
        print("Пишу сценарий в Gemini…")
        scenario = gemini.generate_scenario(args.topic, args.scenes)

    out = args.out or os.path.join("output", f"reel_{datetime.now():%Y%m%d_%H%M%S}.mp4")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    build_video(scenario, out, offline=args.offline, music=args.music, font=args.font,
                scene_duration=args.duration)
    with open(os.path.splitext(out)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)
    print(f"Готово: {out}")

    if args.publish:
        from .instagram import InstagramClient
        InstagramClient().post_reel(out, caption=scenario.get("caption", ""), video_url=args.video_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
