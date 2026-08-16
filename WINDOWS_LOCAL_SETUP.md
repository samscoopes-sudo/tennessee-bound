# Edit your video on your own Windows PC — with Claude Code

Goal: take a video you already have (e.g. your COPD video) and automatically
add **b-roll + burnt-in captions**, driven by Claude Code running on your PC.

Why local: your video and the open internet are both on your machine, so the
agent can transcribe, fetch free b-roll, and compose — no cloud, no GPU.

Cost: **effectively free.** Your Claude subscription is the "brain," captions
(Whisper) and editing (FFmpeg) are free, and b-roll comes from free stock.

> Follow the steps in order. Each **code block** is pasted into a terminal.
> To open a terminal: press the **Windows key**, type **PowerShell**, hit Enter.

---

## Step 1 — Install the four tools
Paste this whole block into PowerShell and press Enter. It uses Windows'
built-in installer (`winget`). Say "yes" if it asks.
```powershell
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
winget install Gyan.FFmpeg
winget install Git.Git
```
**Then close PowerShell and open a fresh one** (so the new tools are found).
Check they installed:
```powershell
node --version; python --version; ffmpeg -version; git --version
```
You should see version numbers for each. If one says "not recognized," tell me
which and I'll help.

## Step 2 — Install Claude Code
```powershell
npm install -g @anthropic-ai/claude-code
```
Then start it and log in with your **existing Claude account** (the same one
you're using now — no extra charge):
```powershell
claude
```
A browser window opens → click **Authorize**. Back in the terminal you're now
in Claude Code. Type `/exit` for now and press Enter.

## Step 3 — Make a project folder and add your video
```powershell
mkdir $HOME\video-edit
cd $HOME\video-edit
```
Now **copy your COPD video file into that folder** (`C:\Users\<you>\video-edit`)
using File Explorer, and **rename it to `source.mp4`** to keep things simple.

## Step 4 — Get a free b-roll key (2 minutes)
1. Go to **https://www.pexels.com/api/** → sign up (free) → copy your API key.
2. Back in PowerShell, save it so Claude can use it:
```powershell
setx PEXELS_API_KEY "PASTE_YOUR_KEY_HERE"
```
Close and reopen PowerShell, then `cd $HOME\video-edit` again.

*(No key? You can skip this and ask for captions only — see the prompt below.)*

## Step 5 — Let Claude Code do the edit
Start Claude Code inside your project folder:
```powershell
cd $HOME\video-edit
claude
```
Then paste this prompt (edit the topic words if you like):

> I have `source.mp4`, an ~11 minute talking-head video about COPD and
> breathing. Please:
> 1. Transcribe it with Whisper (faster-whisper) to get word-level timing.
> 2. Burn in clean, readable captions synced to the speech.
> 3. Add relevant b-roll over the talking parts using free Pexels stock
>    (my PEXELS_API_KEY is set) — search terms like "lungs", "breathing",
>    "inhaler", "doctor", "elderly exercise". Keep my audio throughout.
> 4. Compose the final 1080p video with FFmpeg and save it as `edited.mp4`.
> Install any Python packages you need. Ask me before anything that isn't free.

Claude will install what it needs, run each step, and produce **`edited.mp4`**
in your folder. It may ask permission to run commands — say yes.

*(Captions only? Replace step 3 with "skip b-roll for now.")*

---

## If you get stuck
Copy the exact error text Claude shows and bring it back to me — I'll tell you
the fix. Common first-time snags: needing to reopen PowerShell after installs,
or approving Claude Code's permission prompts. All easily solved.

## Optional: the structured "skill" version
For fancier results (styled captions, smarter b-roll placement) you can add the
open-source video skill into your folder first:
```powershell
git clone https://github.com/Bomx/super-video-maker-skill
```
Then in the prompt add: "Use the super-video-maker-skill in this folder as a
guide, but only the free parts (Whisper captions + free stock b-roll)."
