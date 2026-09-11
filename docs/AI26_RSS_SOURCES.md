# AI26 RSS/Atom sources — sampling manifest documentation

Verified 2026-09-11. Manifests:

- `config/projects/ai26-rss-sources.toml` — RSS/Atom feeds (P1 media,
  institutions, blogs; P2 broad progress imaginary)
- `config/projects/ai26-resistance-sources.toml` — organized AI-resistance
  sources (RSS + web + discovery indexes)

## Running collection

```bash
# RSS (both manifests; canonical collector, one-URL-per-line files also work)
laclaugpt collect rss config/projects/ai26-rss-sources.toml --fetch-article
laclaugpt collect rss config/projects/ai26-resistance-sources.toml --fetch-article

# Web-only resistance sources (no feeds exist; verified 2026-09-11)
laclaugpt collect web https://airesistlist.org/
laclaugpt collect web https://www.stopai.info/
laclaugpt collect web https://evitable.com/in-the-news
laclaugpt collect web https://theprotest.ai/
```

`--fetch-article` is optional; without it records carry the feed summary
only (metadata retains `feed_summary` provenance either way). One dead or
empty feed never fails a run: it is skipped with a JSON `skipped` line.

## Why these feeds are sampled

`paper/PAPER.md` §2.2 treats accelerationism, existential-risk, critical
AI, anti-AI opposition and left-wing techno-optimism as **sensitising
starting points** for examining AI contestation — never as a fixed
typology. Source manifests record `source_family` / `sampling_rationale`
as **sampling heuristics**: provenance that explains why a source entered
the corpus. LaclauGPT infers actual articulations from individual texts;
a publisher is never treated as an ideological ground-truth label, and a
single source can carry several competing imaginaries.

Coverage of candidate imaginaries (sensitising mapping, not ontology):

| Candidate imaginary | Feeds |
|---|---|
| existential-risk / doom / rationalist | LessWrong, MIRI, FLI, METR |
| critical AI / power / labour / rights | AI Now, AlgorithmWatch, Data & Society, Ada Lovelace |
| techno-optimism / acceleration / elite | pmarca, Interconnects, Import AI |
| governance / institutional | Tech Policy Press, Georgetown CSET |
| progress imaginary (broad, P2) | Works in Progress |
| AI-industry elite (already collected) | OpenAI, DeepMind, HuggingFace (private feeds.txt) |
| pause / anti-AGI mobilisation | PauseAI, ControlAI |
| anti-AI / anti-transhumanism / direct action | Stop AI (web) |
| data-centre / infrastructure resistance | Evitable (web), AI Resist List (index) |
| coalition discovery | The AI Protest (index), AI Resist List (index) |

## Feed table (RSS manifests)

| name | feed | family | priority | last verified |
|---|---|---|---|---|
| lesswrong_frontpage | lesswrong.com/feed.xml?view=frontpage | x-risk / rationalist | P1 | 2026-09-11 |
| miri_blog | intelligence.org/feed/ | x-risk / alignment | P1 | 2026-09-11 |
| flinstitute | futureoflife.org/feed/ | x-risk / governance | P1 | 2026-09-11 |
| metr | metr.org/feed.xml | x-risk / evaluations | P1 | 2026-09-11 |
| ai_now | ainowinstitute.org/category/news/feed | critical AI | P1 | 2026-09-11 |
| algorithmwatch | algorithmwatch.org/en/feed/ | critical AI / justice | P1 | 2026-09-11 |
| data_society | datasociety.net/feed/ | critical AI | P1 | 2026-09-11 |
| ada_lovelace | adalovelaceinstitute.org/feed/ | critical AI / governance | P1 | 2026-09-11 |
| pmarca | pmarca.substack.com/feed/ | techno-optimism / acceleration | P1 | 2026-09-11 |
| interconnects | interconnects.ai/feed | frontier-AI elite / bridge | P1 | 2026-09-11 |
| import_ai | importai.substack.com/feed | AI-industry elite | P1 | 2026-09-11 |
| tech_policy_press | techpolicy.press/rss/feed.xml | governance / institutional | P1 | 2026-09-11 |
| cset_georgetown | cset.georgetown.edu/feed/ | governance / natsec | P1 | 2026-09-11 |
| works_in_progress | worksinprogress.co/rss.xml | progress imaginary (P2) | P2 | 2026-09-11 |
| pauseai_news | pauseai.info/rss.xml | pause_ai / xrisk_mobilization | P1 | 2026-09-11 |
| controlai_blog | blog.controlai.org/feed | anti_agi / democratic_control | P1 | 2026-09-11 |

## Rejected / replaced / notes (verification round 2026-09-11)

- **Data & Society** — channel alive (HTTP 200, WordPress) but served 0
  items. Kept `active = true` pending publisher fix; remove at next
  verification if still empty.
- **Ada Lovelace Institute** — same: live channel, 0 items. Kept active.
- **Georgetown CSET** — healthy (10 items).
- **CAES (existentialsafety.org)** — `/feed.xml` is a 301 redirect loop
  (www <-> apex, verified twice). Marked `active = false` as
  `unsupported`; re-check next round. Homepage text is collectable via
  `collect web` if a manual snapshot is needed.
- **No Google News proxies** — all feeds are direct publisher feeds.
- **DAIR** — deliberately NOT duplicated here; the dedicated DAIR AI26
  collector handles that source (see docs/DAIR_COLLECTION.md).
- All 14 P1/P2 RSS feeds: HTTP 200, valid RSS/Atom, recent entries
  verified at fetch time; article URLs resolve; `--fetch-article`
  verified on sample (DeepMind 8.6k chars article text via canonical web
  adapter). Dead feeds yield 0 records without raising.

## Resistance sources (non-RSS)

| org | type | URL | priority | rationale | verified |
|---|---|---|---|---|---|
| PauseAI | rss | pauseai.info/rss.xml | P1 | pause movement, protest, AI-race antagonist | 2026-09-11 |
| ControlAI | rss | blog.controlai.org/feed | P1 | superintelligence prohibition, parliament | 2026-09-11 |
| AI Resist List | discovery_index | airesistlist.org | P1 | cross-dimension resistance map | 2026-09-11 |
| Stop AI | web | stopai.info | P2 | permanent prohibition, anti-transhumanism | 2026-09-11 |
| Stop The AI Race | web | stoptherace.ai | P2 | race antagonist, occupation | 2026-09-11 |
| Evitable | web | evitable.com/in-the-news | P2 | "AI is not inevitable", data-centre opposition | 2026-09-11 |
| CAES | unsupported | existentialsafety.org | P2 | feed 301-loop; re-check | 2026-09-11 |
| The AI Protest | discovery_index | theprotest.ai | P2 | coalition hub; participants evaluated separately | 2026-09-11 |

## Known gaps and biases

1. **RSS covers publishers, not grass-roots discourse.** Contemporary
   e/acc grassroots talk, anti-AI protest, labour mobilisation, data-centre
   opposition, populist/Luddite discourse and left-wing techno-optimism
   are poorly represented by dedicated RSS publishers. These gaps belong
   to the existing social/web/Telegram/Zeeschuimer/Minet collectors and
   future targeted sources. No general news feed pretends to cover them.
2. **First-run backfill**: feeds deliver their full recent history on the
   first collection (Tech Policy Press alone served ~3.9k items); later
   runs are incremental and deduplicated by the canonical
   `CollectionStore` ledger (normalized URL + content hash).
3. **Organizational self-presentation bias**: movement sites describe
   their own campaigns; antagonism constructions must be evidenced in
   text (INV_ANTAGONISM), not inferred from the source list.
4. **`source_family` is provenance, not classification** — downstream
   analysis must not treat it as an ideological code.
5. **Works in Progress** is a broad non-AI publication; it is sampled for
   the progress imaginary with lightweight relevance filtering at the
   analysis stage only — not keyword-filtered at ingestion.