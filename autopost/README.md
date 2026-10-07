# Автопостинг видео в Instagram Reels

Скрипт делает короткий вертикальный ролик (1080×1920, 30 fps, H.264 + AAC) и публикует его в Instagram через официальный Graph API.

Как это работает:
1. Gemini пишет сценарий по теме: подпись к посту и 3–6 сцен (текст на экране + промпт для картинки). Можно вместо этого дать свой JSON.
2. Для каждой сцены Gemini (Nano Banana Pro, `gemini-3-pro-image-preview`) рисует картинку 9:16.
3. ffmpeg собирает ролик: медленный зум на каждой картинке, подпись на плашке, плавные переходы, музыка или тихая дорожка.
4. Ролик загружается в Instagram напрямую с диска (resumable upload) и публикуется как Reels.

## Установка

Нужны Python 3.9+ и ffmpeg.

```bash
pip install -r autopost/requirements.txt
cp autopost/.env.example .env   # и заполнить ключи
```

## Запуск

```bash
# Только собрать ролик по теме (сценарий и картинки от Gemini)
python -m autopost.main --topic "Футболки с принтами от нейросети"

# Собрать и сразу опубликовать
python -m autopost.main --topic "Новая коллекция футболок" --music music.mp3 --publish

# Свой сценарий, без Gemini (картинки-заглушки) — проверить, что ffmpeg всё собирает
python -m autopost.main --scenario autopost/examples/scenario.json --offline
```

Ролик и сценарий сохраняются в `output/`. В сценарии у сцены можно указать `"image": "путь/к/фото.jpg"`, тогда она возьмёт ваше фото вместо генерации, и `"duration"` в секундах.

## Доступ к Instagram API

1. Аккаунт Instagram должен быть профессиональным (Business или Creator).
2. Создайте приложение на developers.facebook.com с продуктом Instagram.
3. Получите долгоживущий токен с правами `instagram_business_basic` и `instagram_business_content_publish` (вход через Instagram, тогда `IG_GRAPH_HOST=graph.instagram.com`) или `instagram_basic` и `instagram_content_publish` (вход через Facebook-страницу, хост по умолчанию `graph.facebook.com`).
4. Впишите `IG_USER_ID` и `IG_ACCESS_TOKEN` в `.env`.

Загрузка видео прямо с диска работает только при входе через Facebook (`graph.facebook.com`). При входе через Instagram (`graph.instagram.com`) Meta требует публичную ссылку на mp4: передайте её через `--video-url`.

Лимит Instagram — 100 публикаций через API за сутки.

## Сеть в облачной среде Claude

Если скрипт запускается в облачной сессии, в сетевой политике среды должны быть разрешены хосты:

- `generativelanguage.googleapis.com` — Gemini;
- `graph.facebook.com` и/или `graph.instagram.com` — Graph API;
- `rupload.facebook.com` — загрузка видео.

На своём компьютере или сервере ничего настраивать не нужно.

## Автозапуск по расписанию

Например, cron каждый день в 18:00:

```
0 18 * * * cd /path/to/Way && python3 -m autopost.main --topic "Футболка дня" --publish >> autopost.log 2>&1
```
