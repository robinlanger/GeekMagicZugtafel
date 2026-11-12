"""Bild per HTTP auf ein GeekMagic SmallTV (Original-Firmware) laden.

Endpunkte laut Community-Dokumentation (u. a. geekmagic-hacs):
  Ultra: POST /doUpload?dir=/image/  ->  /set?theme=3  ->  /set?img=/image/<datei>
  Pro:   POST /doUpload?dir=/image/  ->  /set?theme=4  (Bilderalbum)
"""

from __future__ import annotations

import io
import logging

import requests
from PIL import Image

log = logging.getLogger(__name__)


class GeekMagic:
    def __init__(self, ip: str, profile: str = "ultra", image_name: str = "zugtafel.jpg",
                 timeout: int = 15) -> None:
        self.base = f"http://{ip}"
        self.profile = profile
        self.image_name = image_name
        self.timeout = timeout
        self._activated = False
        self._last_upload: bytes | None = None

    @staticmethod
    def to_jpeg(img: Image.Image, quality: int = 90) -> bytes:
        buf = io.BytesIO()
        # Baseline-JPEG (nicht progressive) – das kann der ESP-Decoder.
        img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=False)
        return buf.getvalue()

    def _get(self, path: str) -> None:
        r = requests.get(self.base + path, timeout=self.timeout)
        r.raise_for_status()

    def upload(self, img: Image.Image) -> bool:
        """Lädt das Bild hoch. Gibt False zurück, wenn es unverändert war."""
        data = self.to_jpeg(img)
        if data == self._last_upload:
            return False
        files = {"file": (self.image_name, data, "image/jpeg")}
        try:
            r = requests.post(f"{self.base}/doUpload?dir=/image/", files=files, timeout=self.timeout)
            r.raise_for_status()
            if not self._activated:
                self._activate()
        except requests.RequestException:
            self._activated = False  # nach Fehlern Anzeige-Modus erneut setzen
            raise
        self._last_upload = data
        return True

    def _activate(self) -> None:
        if self.profile == "pro":
            self._get("/set?theme=4")
        else:
            self._get("/set?theme=3")
            self._get(f"/set?img=/image/{self.image_name}")
        self._activated = True
        log.info("Anzeige auf %s aktiviert (%s)", self.image_name, self.profile)
