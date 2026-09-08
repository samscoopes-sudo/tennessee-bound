"""GenAIPro Veo V2 text-to-video client."""
import os, time, requests
from pathlib import Path

BASE = "https://genaipro.io/api"


class Veo:
    def __init__(self, api_key: str | None = None):
        self.key = api_key or os.environ.get("GENAIPRO_API_KEY", "")
        if not self.key:
            raise ValueError("GenAIPro API key required (pass or set GENAIPRO_API_KEY)")
        self.headers = {"Authorization": f"Bearer {self.key}"}

    def credits(self) -> int:
        r = requests.get(f"{BASE}/v2/veo/credits", headers=self.headers)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data and isinstance(data[0], dict):
            entry = data[0]
            return entry.get("quota", 0) - entry.get("used", 0)
        if isinstance(data, dict):
            return data.get("credits", data.get("balance", 0))
        return 0

    def text_to_video(self, prompt: str, dest: Path,
                      duration: int = 5, aspect_ratio: str = "landscape",
                      number_of_videos: int = 1) -> Path:
        ar_map = {
            "landscape": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "portrait": "VIDEO_ASPECT_RATIO_PORTRAIT",
            "16:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "9:16": "VIDEO_ASPECT_RATIO_PORTRAIT",
        }
        body = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": ar_map.get(aspect_ratio, aspect_ratio),
            "number_of_videos": number_of_videos,
        }
        r = requests.post(f"{BASE}/v2/veo/text-to-video",
                          json=body, headers=self.headers)
        if not r.ok:
            raise RuntimeError(f"{r.status_code}: {r.text}")

        data = r.json()
        histories = data.get("histories", [data] if "id" in data else [])
        if not histories:
            raise RuntimeError(f"No task returned: {data}")
        task_id = histories[0]["id"]
        print(f"  Veo task {task_id} submitted, polling...")
        return self._poll_and_download(task_id, dest)

    def _poll_and_download(self, task_id: str, dest: Path,
                           timeout: int = 600, interval: int = 10) -> Path:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = requests.get(f"{BASE}/v2/veo/tasks/{task_id}",
                             headers=self.headers)
            r.raise_for_status()
            task = r.json()
            status = task.get("status", "")
            if status == "completed":
                urls = task.get("file_urls", [])
                if not urls:
                    raise RuntimeError(f"Completed but no file_urls: {task}")
                return self._download(urls[0], dest)
            elif status == "failed":
                raise RuntimeError(f"Veo task failed: {task.get('error', task)}")
            time.sleep(interval)
        raise TimeoutError(f"Veo task {task_id} timed out after {timeout}s")

    def create_image(self, prompt: str, dest: Path,
                     number_of_images: int = 1) -> Path:
        # Try JSON first, fall back to form-data
        body = {
            "prompt": prompt,
            "number_of_images": number_of_images,
        }
        r = requests.post(f"{BASE}/v2/veo/create-image",
                          json=body, headers=self.headers)
        if r.status_code == 400 and "Prompt is required" in r.text:
            # Try as multipart form data
            r = requests.post(f"{BASE}/v2/veo/create-image",
                              files={"prompt": (None, prompt),
                                     "number_of_images": (None, str(number_of_images))},
                              headers=self.headers)
        if not r.ok:
            raise RuntimeError(f"{r.status_code}: {r.text}")
        data = r.json()
        histories = data.get("histories", [data] if "id" in data else [])
        if not histories:
            raise RuntimeError(f"No task returned: {data}")
        task_id = histories[0]["id"]
        print(f"  Image task {task_id} submitted, polling...")
        return self._poll_and_download(task_id, dest)

    def frames_to_video(self, image_url: str, prompt: str, dest: Path,
                        duration: int = 5,
                        aspect_ratio: str = "landscape") -> Path:
        """Generate video from a reference image URL (hosted on GenAI Pro)."""
        ar_map = {
            "landscape": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "portrait": "VIDEO_ASPECT_RATIO_PORTRAIT",
            "16:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "9:16": "VIDEO_ASPECT_RATIO_PORTRAIT",
        }
        body = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,
            "aspect_ratio": ar_map.get(aspect_ratio, aspect_ratio),
        }
        r = requests.post(f"{BASE}/v2/veo/frames-to-video",
                          json=body, headers=self.headers)
        if not r.ok:
            raise RuntimeError(f"{r.status_code}: {r.text}")
        data = r.json()
        histories = data.get("histories", [data] if "id" in data else [])
        if not histories:
            raise RuntimeError(f"No task returned: {data}")
        task_id = histories[0]["id"]
        print(f"  Frames-to-video task {task_id} submitted, polling...")
        return self._poll_and_download(task_id, dest)

    def _download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"  Downloaded → {dest}")
        return dest
