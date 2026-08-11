# Content Pipeline

Each **episode** follows a fixed spine from teaser to library asset. One live webinar yields one long video plus several shorts over ~2 weeks.

**Channel name:** *FeatureFactory — building in the open*

**Positioning:** We build and evolve the FeatureFactory / Edda playbook using Mimir — viewers learn the platform by watching real methodology work.

---

## Episode spine (per webinar)

The repeatable loop for every episode:

```text
Short teaser  →  Announce webinar  →  Live webinar  →  Long video (edited replay)
       ↑                                                         │
       │              Short clips cut from long video             │
       └──── next episode's teaser (while clips still posting) ──┘
```

| Step | Asset | When | Purpose |
|------|-------|------|---------|
| 1 | **Short teaser** | 3–7 days before live | Prove the outcome in 60s; cold traffic on LinkedIn / communities |
| 2 | **Announce post** | 2–3 days before + day-of | Date, persona, promised outcome; link to register |
| 3 | **Live webinar** | Event day | Code-along + Q&A; raw recording captured |
| 4 | **Long video** | 7–14 days after live | Edited replay on YouTube; SEO + trust for latecomers |
| 5 | **Short clips** (3–4) | After long video is public | Cut from replay; 1–2/day for 3–5 days; link to long form |

**CTA is the same at every step:** Register → connect MCP → run one command from [What Mimir Can Do](../../templates/methodology/use_cases.html).

### First launch (Episode 1 only)

Episode 1 has no prior replay to point at. Order is:

1. **Short teaser** — record natively (e.g. "One command: BPE lands in `.cursor/playbooks`"). No webinar required to produce it.
2. **Announce post** — "Here's what we'll do live on [date]" — teaser makes the invite credible.
3. **Webinar → long video → clip harvest** — same as all later episodes.

---

## Yield per episode

| Asset type | Count | Source |
|------------|-------|--------|
| Short teaser | 1 | Native recording (pre-live) or cut from prior episode |
| Announce posts | 1–2 | Text + link (LinkedIn, email list) |
| Live webinar | 1 | Raw screen recording |
| Long video | 1 | Edited webinar (25–35 min) |
| Short clips | 3–4 | Cut from long video (post-publish) |
| Thank-you email | 1 | ≤24h after live; unlisted replay + survey |

**Steady state:** While shorts from Episode *N* are still posting, the teaser for Episode *N+1* goes out — no dead weeks between webinars.

See [content-calendar.md](./content-calendar.md) for recommended first five episodes and sequencing.

---

## Pipeline overview (repurposing)

```text
PRE-LIVE
  Short teaser (native, 60s)           → LinkedIn, Shorts, communities
  Announce post                        → LinkedIn, email

LIVE
  Webinar (raw recording)

POST-LIVE
  Thank-you email + unlisted replay    → ≤24h
  Long video (edited, 25–35 min)     → YouTube (public at 7–14 days)
    ├─→ Chapters + description SEO
    ├─→ Short clips (3–4 × 60–90 sec) → YouTube Shorts, LinkedIn
    │     └─→ Community posts (link to long video, not signup)
    └─→ Optional: carousel, newsletter snippet, blog excerpt
```

---

## Short-form video

Two roles: **teaser** (before live) and **clip** (after long video).

### Teaser (pre-live)

Record standalone — do not wait for the webinar edit.

| Segment | Duration | Content |
|---------|----------|---------|
| Hook | 0–3 sec | Pain statement |
| Demo | 3–45 sec | One MCP command → one visible result |
| CTA | 45–60 sec | "Free code-along [date] — link in bio" |

### Clip (post-live)

Same template; CTA points to long YouTube video:

| Segment | Duration | Content |
|---------|----------|---------|
| Hook | 0–3 sec | Pain or quote from Q&A |
| Demo | 3–45 sec | Best moment from webinar |
| CTA | 45–60 sec | "Full walkthrough on YouTube" |

**Native short topics** (teasers that need no webinar)

- One command: BPE lands in `.cursor/playbooks`
- Bug fixed the BPE-09 way — `@.cursor/playbooks/Edda/BPE/BPE-09-Fix_Bug.md`
- PR review against playbook activity, not opinion
- Release playbook → PIP required for changes
- Export workflow JSON → import on another team's Mimir

**Export specs**

- 1080×1920 (vertical) for Shorts / LinkedIn mobile
- 1920×1080 (horizontal) optional for LinkedIn desktop
- Burned-in captions (many viewers watch muted)

---

## Long-form video (comprehensive)

**Source:** Edited webinar recording

**Edit checklist**

- [ ] Trim dead air, failed attempts, long silences
- [ ] Add 10-sec title card: persona + outcome
- [ ] Add lower-third once: "Edda = FeatureFactory playbook on Mimir"
- [ ] YouTube chapters matching run-of-show segments
- [ ] Description: links to register, use-cases anchor, DOCKER_QUICK_START
- [ ] Pin comment with CTA and **next webinar date**

**Title template**

```text
[Persona] — [Outcome] | FeatureFactory building in the open
```

Example: `Team Lead — Share your TDD playbook across the program | FeatureFactory building in the open`

---

## LinkedIn promotion

**Cadence:** 2–3 posts per week during launch; 1/week steady state

| Post type | When | Content |
|-----------|------|---------|
| Teaser clip | Pre-live (step 1) | Short video + "Live code-along [date]" |
| Announce | Pre-live (step 2) | Persona, outcome, register link |
| Clip post | Post-long-video | Short cut + link to YouTube |
| Carousel | Post-long-video | 4–5 slides: pain → command → result → CTA |
| Text + link | Anytime | Quote from Q&A; link to replay or next live |

**Hashtags (rotate, don't spam):** `#EngineeringExcellence` `#AIAssistants` `#CursorIDE` `#DevOps` `#Agile` `#KnowledgeManagement`

---

## Community distribution

Post **short teaser or clip**; link to **long YouTube video** (post-live) or **webinar registration** (pre-live).

| Community type | Persona fit | Example angle |
|----------------|-------------|---------------|
| Cursor / AI IDE | Lead Engineer, Junior | Export workflow to `.cursor/playbooks` |
| Platform / DevOps | Release Engineer | Infra blueprints as shareable playbook |
| Agile / SM | Scrum Master | Sprint readiness from BPE |
| Engineering leadership | CC Head | Knowledge retention + v1.0 release |
| Product / PO | Product Owner | POC using Edda methodology |

**Rule:** Lurk first; contribute answer; share clip only when relevant to thread.

---

## Release timing

| Asset | When |
|-------|------|
| Short teaser | 3–7 days before live |
| Announce post | 2–3 days before + morning of live |
| Thank-you email + unlisted replay | ≤24h after live |
| Long video public on YouTube | 7–14 days after live |
| Short clips (from replay) | 1–2 per day for 3–5 days after long video goes public |
| Next episode teaser | Overlap with clip posting (no gap week) |
| Community posts | Stagger across 2 weeks per episode |

### Example week map (Episode 2+)

| Week | Mon–Tue | Wed–Thu | Fri | Following week |
|------|---------|---------|-----|----------------|
| Pre-live | Teaser post | Announce post | **Live webinar** | Thank-you email |
| Post-live | — | — | — | Edit; long video when ready |
| Clips | — | — | — | Long public + 3–4 clips; next teaser starts |

---

## Metrics (track per episode)

| Metric | Tool |
|--------|------|
| Teaser impressions | LinkedIn / YouTube Shorts |
| Registrations / show-up | Event platform |
| Replay views | YouTube Analytics |
| Short clip impressions | LinkedIn / YouTube Shorts |
| MCP connect (proxy) | Post-event survey |
| FOB registrations (attributed) | UTM on all links |

**UTM pattern:** `?utm_source=youtube&utm_medium=video&utm_campaign=ep01-lead-engineer-bpe-export`

Variations:

- Teaser: `utm_medium=teaser`
- Announce: `utm_medium=announce&utm_source=linkedin`
- Long replay: `utm_medium=video`
