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
        if isinstance(data, dict):
            return data.get("credits", data.get("balance", 0))
        if isinstance(data, list) and data:
            return data[0] if isinstance(data[0], int) else 0
        if isinstance(data, (int, float)):
            return int(data)
        print(f"  Credits response: {data}")
        return 0

    def text_to_video(self, prompt: str, dest: Path,
                      duration: int = 5, aspect_ratio: str = "16:9",
                      number_of_videos: int = 1) -> Path:
        body = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "number_of_videos": number_of_videos,
        }
        r = requests.post(f"{BASE}/v2/veo/text-to-video",
                          json=body, headers=self.headers)
        r.raise_for_status()
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

    def _download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"  Downloaded → {dest}")
        return dest
