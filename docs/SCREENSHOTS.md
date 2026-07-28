# Screenshot Capture Instructions

Three screenshots are referenced by the [README](../README.md) and don't exist yet — this document is the exact recipe for producing them so they match what's described. Take all three in one sitting so the theme, browser chrome, and data are consistent.

**Before you start:**
1. `./start.sh` from the repo root, wait for both servers to report ready
2. Open **http://localhost:5173** in Chrome (or your preferred browser) in a normal, non-incognito window
3. Confirm Settings → Theme is set to **Dark** (the default) — all three shots should be dark mode for visual consistency
4. Resize the browser window to exactly **1512×982** (a common MacBook-class viewport) before capturing any of them. On macOS you can check the current size with the Chrome DevTools device toolbar, or use a window-resizing utility — the exact number matters less than **using the same size for all three**
5. Save every file as a **PNG**, not JPEG — the UI has flat color fills and text that compress better and stay crisper as PNG

Save all three into `docs/screenshots/` using the exact filenames below — the README embeds them by that literal path.

---

## 1. `hero.png`

**Page:** Chat (`/`), empty state — no query submitted yet.

**Steps:**
1. Navigate to `/` fresh (reload if you have existing history — the empty state only shows when there are no messages in the *current session's* chat view, so a fresh page load is enough even with history in the sidebar)
2. Make sure the History sidebar is **expanded** (left arrow toggle, top-left) and has at least 2–3 real entries in it, so the screenshot shows a populated, lived-in app rather than a blank first-run
3. Capture the full browser viewport: top nav (logo, Chat/Leaderboard/Settings tabs, theme toggle), history sidebar, the "Ask once, hear from multiple agents" empty-state message, and the input bar at the bottom with all four action icons (attach file, attach image, mic, send) visible

**Why this one:** it's the first image anyone sees in the README — it needs to communicate "multi-agent chat app" at a glance without requiring the reader to read any text.

**Save as:** `docs/screenshots/hero.png`

---

## 2. `live-progress.png`

**Page:** Chat (`/`), mid-query — agent dispatch in progress.

**Steps:**
1. In the input bar, type exactly: `Explain what recursion is in one paragraph.`
2. Press send
3. Watch the agent cards — you want a screenshot where **some cards have already resolved (green check, latency, score) and others are still "waiting" or "running"** — this is the one screenshot that needs precise timing, not a stable end state
4. In practice: Groq resolves almost immediately (under 1s), Mistral shortly after, Gemini and Cohere take longer (multiple seconds). The best capture window is right after Groq and Mistral finish but before Gemini/Cohere do — you should have a visible mix of resolved and in-progress cards
5. If you miss the window, just resubmit the same prompt (or `./start.sh` restart if you want a clean history) and try again — this may take 2–3 attempts to time correctly
6. Capture the full viewport: the "Dispatching to 4 agents" header with the X/4 progress bar clearly showing a partial count (e.g. "2/4 done"), and all four agent cards in their differing states

**Why this one:** it's the feature that most differentiates this from a single-model chat UI — the README's "live agent dispatch" claim needs visual proof.

**Save as:** `docs/screenshots/live-progress.png`

---

## 3. `comparison-view.png`

**Page:** Chat (`/`), after the same query from step 2 has fully completed.

**Steps:**
1. Let the query from the previous screenshot finish completely (synthesized answer visible)
2. Scroll so the viewport shows: the synthesized answer panel (with the confidence gauge and attribution chips), **and** as much of the comparison table below it as fits — the table header row plus at least 3 of the 4 agent rows should be visible
3. If the confidence gauge and full table can't both fit in one viewport at 1512×982, prioritize the synthesized answer + gauge + attribution chips at the top, with the comparison table visible even if partially cut off at the bottom — do not zoom out or change browser zoom level to force it to fit, since that will make text blurry
4. Do **not** expand any individual agent's collapsible response card for this shot — the comparison table in its collapsed-cards state is the point

**Why this one:** demonstrates the scoring/synthesis output — the actual product of the pipeline, not just its process.

**Save as:** `docs/screenshots/comparison-view.png`

---

## After capturing

Confirm all three files exist and render correctly:

```bash
ls -la docs/screenshots/
```

Then verify the README's image links resolve by previewing it in a Markdown renderer that supports relative image paths (GitHub's own preview, or VS Code's Markdown preview). Broken image icons mean a filename or path mismatch — the README expects exactly `docs/screenshots/hero.png`, `docs/screenshots/live-progress.png`, and `docs/screenshots/comparison-view.png`, case-sensitive.
