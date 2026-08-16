# Run this on Google Cloud's free $300 credit — step by step

This guide gets the **whole automatic pipeline** running on a rented GPU
machine, paid for by Google Cloud's free starter credit. You paste a script,
you get back an edited talking-head avatar video.

> **Honest expectations first**
> - This takes about **1 hour** the first time. It's copy-paste, not coding,
>   but it is fiddly.
> - You need a **credit/debit card** to verify the Google account. You are
>   **not charged** while the free credit lasts (~$300, 90 days). A GPU is a
>   few $/hour, so the credit covers **many hours**.
> - **Always stop the machine when you're done** (Step 8) or the credit drains.
> - This is open-source software — the first run may need a small fix. Come
>   back and I'll help you debug whatever error you see.

---

## Step 1 — Make a Google Cloud account
1. Go to **https://cloud.google.com** and click **"Get started for free."**
2. Sign in with a Google account, add a card to verify. You'll see the
   **~$300 free credit** appear.

## Step 2 — Ask for GPU access (may take a few hours)
New accounts start with a GPU limit of zero, so you request one:
1. In the search bar at the top, type **"Quotas"** and open it.
2. Filter for **"GPUs (all regions)"**, tick it, click **"Edit Quotas."**
3. Request a limit of **1**. Approval is often minutes, sometimes a day.

*(If you skip this, Step 4 will fail with a "quota" error — that's the sign you
still need this step.)*

## Step 3 — Create the GPU machine
1. Search **"VM instances"** → **"Create instance."**
2. Set these:
   - **Name:** `avatar-machine`
   - **Region:** one that has GPUs (e.g. `us-central1`)
   - **Machine / GPU:** add **1 × NVIDIA T4** (the cheapest that works)
   - **Boot disk:** click "Change" → pick an image with GPU drivers
     preinstalled: **"Deep Learning VM"** (Debian, CUDA) → set size to **60 GB**.
   - **Firewall:** tick **"Allow HTTP traffic."**
3. Click **Create.** Wait ~1 minute.

## Step 4 — Open the machine's terminal
On the new machine's row, click **"SSH."** A black terminal window opens in your
browser. Everything below is pasted **there** (right-click to paste).

## Step 5 — Open the web port (one-time)
So you can reach the app in your browser, run:
```bash
gcloud compute firewall-rules create allow-8000 --allow tcp:8000 || true
```

## Step 6 — Install Docker + the code, then start everything
Paste this whole block. It installs the tools, downloads your project, and
starts all four services. **The first start downloads ~30 GB, so give it
15–30 minutes.**
```bash
# tools
sudo apt-get update && sudo apt-get install -y git docker-compose-plugin
# make sure the GPU is visible to Docker (Deep Learning VM has the toolkit)
sudo nvidia-smi >/dev/null && echo "GPU OK"

# get your project
git clone https://github.com/samscoopes-sudo/tennessee-bound.git
cd tennessee-bound

# your AI key (the director) — paste your real key between the quotes
echo 'ANTHROPIC_API_KEY=PASTE_YOUR_KEY_HERE' > .env
echo 'PEXELS_API_KEY=' >> .env      # optional, free b-roll; leave blank to skip

# start the whole stack
sudo docker compose -f docker-compose.gpu.yml up -d
```

Get a free **ANTHROPIC_API_KEY** at https://console.anthropic.com (add ~$5).
Get a free **PEXELS_API_KEY** (optional, for real b-roll) at
https://www.pexels.com/api.

## Step 7 — Use it
1. Back on the VM instances page, copy the machine's **External IP**.
2. In your browser go to: **`http://THAT-IP:8000`**
3. Check it's alive: `http://THAT-IP:8000/health` should show
   `"duix_avatar_enabled": true`.
4. Make a video — send it a script, a face reference video, and a short voice
   sample:
   ```bash
   curl -F script="Hi everyone, welcome to today's video..." \
        -F face_video=@face.mp4 \
        -F voice_reference=@my_voice.wav \
        http://THAT-IP:8000/api/avatar-jobs
   ```
   It returns a job id. Check progress at
   `http://THAT-IP:8000/api/jobs/THE-ID`, and when it says `done`, download at
   `http://THAT-IP:8000/api/jobs/THE-ID/download`.

   *(`face.mp4` = a short clip of the face to animate; `my_voice.wav` = a short
   clean voice sample to clone. Reuse the same two files every time and your
   presenter stays consistent.)*

## Step 8 — STOP the machine (important!)
When you're done making videos:
- VM instances page → tick `avatar-machine` → **"Stop."**

Stopped = you pay almost nothing. Press **"Start"** next time you want to make
videos; your setup is still there, just run
`cd tennessee-bound && sudo docker compose -f docker-compose.gpu.yml up -d` again.

---

## If something goes wrong
Run this to see what each service is saying, copy the error, and bring it back
to me:
```bash
cd tennessee-bound && sudo docker compose -f docker-compose.gpu.yml logs --tail=50
```
The most likely first-run snags are the GPU not being visible to Docker, the
model download still finishing, or a small file-path mismatch in the avatar
step — all fixable. Paste me the log and I'll tell you the exact fix.
