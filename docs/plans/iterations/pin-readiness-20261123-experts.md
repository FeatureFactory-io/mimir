# PIN-01 Experts readiness — 23 November 2026

Goal: rebuild the full Experts & Karma feature from the pre-Experts baseline,
recording the ESM → PIN → BPE/MIN → verification → reviewed release story.

| Gate | Evidence | Result |
| --- | --- | --- |
| BSP | Makefile and requirements.txt | Pass |
| Journey | user_journey.md, Act 18, Elena/Bob/Maria | Pass |
| Living specs | Six Act 18 files, navigation additions | Pass: 49 AT contracts, not implemented |
| Architecture | SAO planned Experts delta and §17 | Pass for planning |
| DSP | CLAUDE.md plus scoped replay AGENTS.md | Pass |
| Agent harness | BaseLLM, ScriptedLLM, agent_story and helper tests | Pass for planning; feature proofs pending |
| Mockups | Actual DEBUG-gated /mockups/experts/ recipes | Present, reviewed; use ESM-06 precedence |

Recorded prerequisite checks: 18 pytest support/mockup-gating tests passed;
one real Django-client AT health scenario passed, three steps. Ruff and Black
checks passed on the scoped new Python files. Nine feature files parse; all 58
contract IDs are unique (49 AT, five browser, four manual UAT). All eleven
people's source and category totals reconcile. No passing Experts behavior is
claimed. The actual 77-render matrix is prototype evidence only.

## PIN-02 scope decision pending

The full acceptance scope has 49 contracts before outline expansion and crosses
new ledger/projection, existing authorization, clipboard, export, PIP lifecycle,
mail, public summary generation and browser UI. Under PIN-02 Step 3b this is a
large, complex iteration requiring an explicit choice. The user has been offered
full-scope planning or smaller delivery iterations preserving the entire film
and feature goal. No scenario is dropped or deferred by assumption.

Do not create the final `pin-orient-20261123.md` until that answer is recorded:
PIN's resume rule treats its presence as completed orientation. Do not dispatch
PIN-03 scenario workers or publish a manifest claiming confirmed scope yet.
The eventual human GO is a later, separate gate on the concrete published
skeleton/issue contract, not this scope choice.

## Learning-log evidence

Three existing ITER Markdown reports were inspected. They lack the current
standard YAML metrics. One reports velocity ratio 1.0 and an environment
mismatch; another reports no drift but only skipped checkpoints. No defensible
five-iteration trend or footprint-accuracy ratio can be computed: unknown.
Do not reuse the legacy claim that skipped feature checks establish a pass.
The old canvas recommendations do not establish a pending Experts architecture
change. Current replay risks: Docker startup failure (host fallback recorded),
locked native editor (CLI/browser recording continues), missing feature adapter
and bindings (planned), and scope size (decision pending).

## Contract clarification to include in review

Public summaries exclude all unpublished PIP content. For authorized get_pip,
self-consumption means creator or target-playbook author. A third-party eligible
reader credits the target-playbook author. Mike's existing staff role supplies
the eligible fixture case; Maria receives no new privilege. These decisions are
explicit in the specifications/data/SAO and remain reviewable before PIN GO.
