"""Публикация Reels через официальный Instagram Graph API.

Видео загружается напрямую с диска (resumable upload через rupload.facebook.com),
поэтому хостить файл по публичной ссылке не нужно. Если ссылка уже есть,
можно передать video_url.

Нужны: IG_USER_ID (ID профессионального аккаунта Instagram) и IG_ACCESS_TOKEN
с правами instagram_basic + instagram_content_publish (вход через Facebook)
или instagram_business_basic + instagram_business_content_publish (вход через Instagram).
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH_HOST = os.environ.get("IG_GRAPH_HOST", "graph.facebook.com")  # или graph.instagram.com
API_VERSION = os.environ.get("IG_API_VERSION", "v23.0")
UPLOAD_HOST = "rupload.facebook.com"


class InstagramError(RuntimeError):
    pass


def _request(url, method="GET", params=None, data=None, headers=None, timeout=120):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise InstagramError(f"{method} {url.split('?')[0]} -> {e.code}: "
                             f"{e.read().decode(errors='replace')[:500]}") from e


class InstagramClient:
    def __init__(self, user_id=None, token=None):
        self.user_id = user_id or os.environ.get("IG_USER_ID")
        self.token = token or os.environ.get("IG_ACCESS_TOKEN")
        if not self.user_id or not self.token:
            raise InstagramError("Нужны IG_USER_ID и IG_ACCESS_TOKEN")
        self.base = f"https://{GRAPH_HOST}/{API_VERSION}"

    def _graph(self, path, method="GET", **params):
        params["access_token"] = self.token
        return _request(f"{self.base}/{path}", method=method, params=params)

    def create_reel_container(self, caption, video_url=None, share_to_feed=True, thumb_offset_ms=None):
        params = {"media_type": "REELS", "caption": caption,
                  "share_to_feed": "true" if share_to_feed else "false"}
        if video_url:
            params["video_url"] = video_url
        else:
            params["upload_type"] = "resumable"
        if thumb_offset_ms is not None:
            params["thumb_offset"] = str(thumb_offset_ms)
        return self._graph(f"{self.user_id}/media", method="POST", **params)["id"]

    def upload_video(self, container_id, video_path):
        size = os.path.getsize(video_path)
        with open(video_path, "rb") as f:
            data = f.read()
        result = _request(
            f"https://{UPLOAD_HOST}/ig-api-upload/{API_VERSION}/{container_id}",
            method="POST", data=data, timeout=600,
            headers={"Authorization": f"OAuth {self.token}", "offset": "0",
                     "file_size": str(size), "Content-Type": "application/octet-stream"},
        )
        if not result.get("success"):
            raise InstagramError(f"Загрузка не удалась: {result}")

    def wait_until_ready(self, container_id, timeout=600, interval=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            info = self._graph(container_id, fields="status_code,status")
            code = info.get("status_code")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise InstagramError(f"Instagram не обработал видео: {info}")
            time.sleep(interval)
        raise InstagramError("Не дождались обработки видео")

    def publish(self, container_id):
        return self._graph(f"{self.user_id}/media_publish", method="POST", creation_id=container_id)["id"]

    def permalink(self, media_id):
        return self._graph(media_id, fields="permalink").get("permalink")

    def post_reel(self, video_path=None, caption="", video_url=None, log=print):
        log("Создаю контейнер Reels…")
        container = self.create_reel_container(caption, video_url=video_url)
        if not video_url:
            log(f"Загружаю {video_path}…")
            self.upload_video(container, video_path)
        log("Жду, пока Instagram обработает видео…")
        self.wait_until_ready(container)
        media_id = self.publish(container)
        log(f"Опубликовано: {self.permalink(media_id) or media_id}")
        return media_id
