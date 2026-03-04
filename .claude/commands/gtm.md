---
description: Go-to-market strategy, quick wins checklist, and NAR Web Server Issue deadline tracker for the GEO Survival Analysis app
user-invocable: true
---

# Go-to-Market Strategy

## One-Sentence Pitch
> "We automate the 3-week manual pipeline that turns a GEO dataset search into a ranked, cross-validated biomarker list — in under 5 minutes, with no coding required."

## Unique Moat
Competitors (KMplot, GEPIA2, OncoLnc, cBioPortal) are locked to TCGA/GTEx. This tool analyzes ALL of GEO (thousands of studies) and validates biomarkers across multiple independent datasets — reproducible cross-cohort meta-analysis that single-study tools cannot offer.

---

## Target Customers (Ranked by Conversion Speed)

| Tier | Who | Pain | Discovers Via |
|------|-----|------|--------------|
| 1 (days) | Wet-lab cancer biologist (PI/postdoc) | "Which of my 6 genes do I spend $40k validating in mice?" | Twitter, BioRxiv, Google |
| 1 (days) | Bioinformatics PhD student | "I'm rewriting the same GEO pipeline for the 5th time" | GitHub, Biostars, r/bioinformatics |
| 1 (days) | Rare cancer researcher | "My cancer isn't in KMplot at all" | Same channels; immediately loyal |
| 2 (weeks) | Aging/longevity biologist | No good cross-study tool outside cancer | Aging Cell, Twitter #aging |
| 2 (weeks) | Translational postdoc | Needs independent validation cohorts for paper | PubMed, BioRxiv |
| 3 (months) | Pharma translational scientist | Procurement-gated; needs SLA | LinkedIn, conferences |

---

## Quick Wins Checklist

### Immediate (This Week)
- [ ] Create Zenodo DOI (zenodo.org → connect GitHub → create release) — *20 min, required for citations*
- [ ] Write GitHub README with demo GIF (screen-record one successful analysis) — *2 hrs, baseline credibility*
- [ ] Submit to OmicTools (omictools.com) — *15 min, Google-indexed within days*
- [ ] Post on r/bioinformatics — "Show HN"-style, origin story + screenshots, no marketing tone — *1 hr, fastest path to 100–500 signups*
- [ ] Twitter thread: hook ("KMplot/GEPIA2 only cover TCGA. I built...") + screenshots + link — *30 min*
- [ ] Open PR on awesome-bioinformatics GitHub list — *30 min, curated discovery*

### This Month
- [ ] Run validation on TP53/VEGFA/CDH1 across 8+ GEO cohorts — document that results match literature — *3 hrs, scientific credibility anchor*
- [ ] Cold email 10 targeted PIs: run THEIR gene through the tool first, send personalized results — *3 hrs*
- [ ] Post tool on Biostars (News section — tool announcements are explicitly allowed)
- [ ] Write methodology blog post: "Why single-dataset KM curves are unreliable" (Medium or own site)
- [ ] Create protocols.io walkthrough for one specific cancer type

### Medium-Term (Before April 2026)
- [ ] **NAR Web Server Issue submission** — see below
- [ ] Fix 5 product gaps before major marketing push (see below)
- [ ] Implement free tier with academic email gate

---

## NAR Web Server Issue — #1 Long-Term Leverage Action

**What it is:** Nucleic Acids Research publishes a special Web Server Issue every July. Every major bioinformatics web tool is in it: Ensembl, BLAST, UCSC Genome Browser, etc. Inclusion generates ~1,000+ registered users and permanent citation compounding.

**Submission deadline:** Typically March/April each year (for July publication)
**Current deadline: ~April 2026** — start drafting NOW

**Journal URL:** https://academic.oup.com/nar/pages/web_server_issue

**What the paper needs:**
- Tool description and motivation (what problem it solves)
- Methods section: analysis pipeline, statistical methods (Cox, KM, meta-analysis approach)
- Validation: show tool reproduces known results (e.g., BRCA1 in breast cancer)
- Novel result: show something new the tool found
- Availability: URL, GitHub link, Zenodo DOI
- Typically 4–6 pages, peer reviewed

**Draft status:** [ ] Not started / [ ] In progress / [ ] Submitted

---

## Product Gaps Blocking Launch

Fix these before the Reddit post or NAR submission:

| Priority | Feature | Roadmap ID | Why It Blocks |
|----------|---------|------------|---------------|
| 1 | CSV export | F04 | Without export, tool is a demo not a workflow step |
| 2 | Forest plots | F08 | Required visualization for meta-analysis publications |
| 3 | Progress streaming | F05 | 5-min analysis with blank screen → users close the tab |
| 4 | Persistent results | F07 | Results gone next day = tool never trusted for real work |
| 5 | Shareable permalink | F09 | Researchers need URLs to cite in paper Methods sections |

---

## Discovery Channels (Ranked by Impact)

1. **NAR Web Server Issue** — permanent, compounds forever
2. **r/bioinformatics** — 260k members, tool posts are welcomed, can drive 100–500 signups
3. **Twitter/X** — #bioinformatics #genomics #cancerresearch #openscience — one viral thread = 50k+ impressions
4. **GitHub** — topics: survival-analysis, cancer-genomics, GEO, kaplan-meier, biomarker-discovery
5. **Biostars + SEQanswers** — answer questions then mention tool; tool announcement post allowed
6. **OmicTools + awesome-bioinformatics** — free, permanent, Google-indexed
7. **Cold emails to PIs** — personalized + real results = ~30% response rate
8. **protocols.io** — cited in Methods sections, compounds with every paper
9. **Conference posters** — AACR (April), ISMB, ASHG (October) — 50 high-quality contacts per event

---

## Proof Points for Scientists

1. **Reproduce a known result** — TP53 in lung adenocarcinoma across 8+ GEO cohorts → credibility anchor
2. **Novel result unavailable elsewhere** — gene significant in 12 PAAD GEO datasets not in KMplot → irreplaceable value
3. **Transparent statistics** — Cox p-values, HRs, CI bands must be visible; scientists distrust hidden math
4. **Comparison table** — answer "why not just use KMplot?" preemptively on the landing page

---

## Pricing Summary

| Tier | Price | Key Limits |
|------|-------|-----------|
| Free | $0 (academic email) | 10 analyses/month, no export, 30-day results |
| Academic Pro | $29/mo or $249/yr | Unlimited, CSV/PNG export, persistent results |
| Lab/Team | $149/mo (5 seats) | Shared workspace, history |
| Enterprise | Custom (~$500+/mo) | Unlimited seats, private deploy, SLA |

**Rules:** No per-query metering. No credit card for free tier. Enterprise = "contact us."
**Conversion triggers:** Export blocked on free, analysis limit banner, 3-email drip onboarding.
