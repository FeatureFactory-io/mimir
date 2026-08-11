# Content Pipeline

Repurpose every live webinar into long-form library content and short-form discovery clips.

## Pipeline overview

```text
Live webinar (raw recording)
  ├─→ Long video (25–35 min, edited)     → YouTube channel
  │     └─→ Chapters + description SEO
  ├─→ Short clips (3–5 × 60–90 sec)      → YouTube Shorts, LinkedIn
  │     └─→ Community posts (link to long video)
  └─→ Email + blog snippet               → Newsletter, LinkedIn article (optional)
```

**Channel name:** *FeatureFactory — building in the open*

**Positioning:** We build and evolve the FeatureFactory / Edda playbook using Mimir — viewers learn the platform by watching real methodology work.

## Long-form video (comprehensive)

**Source:** Edited webinar recording

**Edit checklist**

- [ ] Trim dead air, failed attempts, long silences
- [ ] Add 10-sec title card: persona + outcome
- [ ] Add lower-third once: "Edda = FeatureFactory playbook on Mimir"
- [ ] YouTube chapters matching run-of-show segments
- [ ] Description: links to register, use-cases anchor, DOCKER_QUICK_START
- [ ] Pin comment with CTA and next webinar date

**Title template**

```text
[Persona] — [Outcome] | FeatureFactory building in the open
```

Example: `Team Lead — Share your TDD playbook across the program | FeatureFactory building in the open`

## Short-form video (discovery)

**Lengths:** 60–90 sec (LinkedIn); up to 60 sec (Shorts)

**Template**

| Segment | Duration | Content |
|---------|----------|---------|
| Hook | 0–3 sec | Pain statement ("Every team's AI invents its own standards") |
| Demo | 3–45 sec | One MCP command → one visible result (screen recording) |
| CTA | 45–60 sec | "Full walkthrough on YouTube" + handle / link |

**Native short topics** (no webinar required)

- Bug fixed the BPE-09 way — `@.cursor/playbooks/Edda/BPE/BPE-09-Fix_Bug.md`
- PR review against playbook activity, not opinion
- Release playbook → PIP required for changes
- Export workflow JSON → import on another team's Mimir

**Export specs**

- 1080×1920 (vertical) for Shorts / LinkedIn mobile
- 1920×1080 (horizontal) optional for LinkedIn desktop
- Burned-in captions (many viewers watch muted)

## LinkedIn promotion

**Cadence:** 2–3 posts per week during launch; 1/week steady state

| Post type | Content |
|-----------|---------|
| Clip post | Short video + 2-sentence hook + link to long video |
| Carousel | 4–5 slides: pain → command → result → CTA (screenshots from webinar) |
| Text + link | Quote from Q&A; link to replay |

**Hashtags (rotate, don't spam):** `#EngineeringExcellence` `#AIAssistants` `#CursorIDE` `#DevOps` `#Agile` `#KnowledgeManagement`

## Community distribution

Post **short clip** or **one concrete tip**; link to **long YouTube video**, not webinar signup.

| Community type | Persona fit | Example angle |
|----------------|-------------|---------------|
| Cursor / AI IDE | Lead Engineer, Junior | Export workflow to `.cursor/playbooks` |
| Platform / DevOps | Release Engineer | Infra blueprints as shareable playbook |
| Agile / SM | Scrum Master | Sprint readiness from BPE |
| Engineering leadership | CC Head | Knowledge retention + v1.0 release |
| Product / PO | Product Owner | POC using Edda methodology |

**Rule:** Lurk first; contribute answer; share clip only when relevant to thread.

## Release timing

| Asset | When |
|-------|------|
| Thank-you email + unlisted replay | ≤24h after live |
| Long video public on YouTube | 7–14 days after live |
| Short clips | 1–2 per day for 3–5 days after long video goes public |
| Community posts | Stagger across 2 weeks per episode |

## Metrics (track per episode)

| Metric | Tool |
|--------|------|
| Registrations / show-up | Event platform |
| Replay views | YouTube Analytics |
| Short clip impressions | LinkedIn / YouTube Shorts |
| MCP connect (proxy) | Post-event survey |
| FOB registrations (attributed) | UTM on all links |

**UTM pattern:** `?utm_source=youtube&utm_medium=video&utm_campaign=ep01-lead-engineer-bpe-export`
