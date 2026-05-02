---
name: nar-submission
description: NAR Web Server Issue submission tracker for GEO Survival Analysis. Shows requirements status, gaps, and next actions. Use when checking NAR submission readiness, updating checklist progress, or planning what to work on next for the journal submission.
user-invocable: true
---

# NAR Web Server Issue — Submission Tracker

**Target:** Nucleic Acids Research Web Server Issue, July 2027  
**Proposal portal:** nar.bihealth.de  
**Contact editor:** Dr. Dominik Seelow

## Timeline

| Milestone | Date | Status |
|-----------|------|--------|
| Proposal submission deadline | December 20, 2026 | ⏳ 8 months away |
| Proposal reply from editors | ~mid-February 2027 | ⏳ |
| Manuscript submission deadline | ~3 weeks after approval, or January 15 2027 latest | ⏳ |
| Manuscript reviews complete | ~mid-April 2027 | ⏳ |
| Publication | July 2027 | ⏳ |

> July 2026 cycle was missed (proposal was due December 2025).

---

## Technical Requirements

Update status symbols as work completes: ✅ PASS · ❌ FAIL · ⚠️ PARTIAL/VERIFY · ⏳ TODO

| Requirement | Status | Notes |
|---|---|---|
| Functional via web browser | ✅ PASS | React + FastAPI |
| HTTPS on standard port 443 | ❌ TODO | Provision Hetzner CX32, register geosurv.io, push to deploy. All deployment files exist (docker-compose.yml, Caddyfile, .github/workflows/deploy.yml) |
| Cookie consent form | ✅ PASS | `frontend/src/components/CookieConsent.tsx` |
| Sample data with one-click load button | ⚠️ PARTIAL | Example queries listed on landing page but no single button that pre-fills + auto-runs |
| Help page with links to sample output | ⚠️ PARTIAL | `HelpPage.tsx` exists; needs links to real persisted result URLs once deployed |
| Data privacy (users can't see each other's submissions) | ✅ PASS | Per-user auth; public access only via explicit permalink |
| Status reporting / link to results for long jobs | ✅ PASS | SSE streaming progress + shareable permalink |
| Email address NOT required | ✅ PASS | Registration accepts username + password only |
| Free access statement on landing page | ✅ PASS | Green box: "This website is free and open to all users and there is no login requirement." |
| Rich output (visualizations, hyperlinks) | ✅ PASS | KM curves, volcano plot, forest plot, CSV/ZIP export |
| No login required to run analysis | ✅ PASS | `/api/search` uses `get_optional_current_user`; login only needed to save history |
| No Flash / Java plugins | ✅ PASS | Pure React frontend |
| No tracking cookies | ⚠️ VERIFY | CookieConsent exists; audit frontend bundle for any 3rd-party analytics |
| No guest login | ✅ PASS | Anonymous or real account only; no "guest" button |
| Not restricted to single/few species | ✅ PASS | Searches all of NCBI GEO |
| Added value beyond simple tool chaining | ✅ PASS | Cross-cohort meta-analysis, NL queries, AI chat — must be argued clearly in manuscript |
| No excessive preprocessing required from users | ✅ PASS | NL query → results directly |
| LICENSE file in repository root | ❌ FAIL | README says MIT but `/LICENSE` file does not exist |
| CI/CD pipeline | ✅ EXISTS | `.github/workflows/deploy.yml` exists; needs `HETZNER_HOST` + `HETZNER_SSH_KEY` GitHub secrets |

---

## Manuscript Requirements

| Requirement | Status | Notes |
|---|---|---|
| Software name as first word(s) of title | ✅ PASS | "GEO Survival Analysis: ..." |
| Valid public URL in abstract | ❌ TODO | Will be `https://geosurv.io` — blocked on deployment |
| Description of input, computations, output | ⚠️ PARTIAL | README covers it; needs formal manuscript section |
| Comparison with existing methods section | ⚠️ PARTIAL | README has table (KMplot / GEPIA2 / OncoLnc); needs dedicated manuscript section |
| One or more biological use case studies | ❌ MISSING | Run a real analysis (e.g., lung adenocarcinoma) and document biological findings |
| Prior peer-reviewed validation | ❌ RISK | NAR discourages tools <1 year old or without prior validation publication; must address in proposal |
| Supplementary data available at submission | ❌ NOT READY | |
| Graphical abstract | ❌ MISSING | Workflow diagram: NL query → GEO download → Cox regression → KM + forest plots |
| Cover letter listing similar tools + URLs | ❌ MISSING | KMplot, GEPIA2, OncoLnc, SurvExpress, TIMER, Xena, cBioPortal |
| 6 referee suggestions (name / institute / email) | ❌ MISSING | Must work independently with bioinformatics / survival analysis expertise |
| NAR Word or LaTeX manuscript file | ❌ MISSING | Use official NAR template |
| Key Points box (2-3 bullets) | ❌ MISSING | |
| Affirmative free-access statement in manuscript body | ✅ READY | Copy from app landing page |
| Software completely functional + extensively tested | ⚠️ PARTIAL | No automated tests; write `uv run pytest` tests or at minimum a manual test checklist |

---

## Priority Action List

Work through these in order — each unblocks the next.

- [ ] **1. Provision Hetzner CX32 + register geosurv.io**  
  Go to Hetzner Cloud console → create CX32 (Ubuntu 24.04). Register geosurv.io at Cloudflare → add A record to server IP. This unblocks the public URL, sample output links, and eventually the proposal.

- [ ] **2. Configure GitHub secrets + first deploy**  
  Add `HETZNER_HOST` (server IP) and `HETZNER_SSH_KEY` to GitHub repo secrets. Push to `development` branch → CI builds image, pushes to GHCR, SSHes in and starts Docker Compose. Verify `https://geosurv.io` is live.

- [ ] **3. Add MIT LICENSE file to repo root**  
  Create `/LICENSE` with standard MIT text (author: Korkodnov I., year: 2026). 2-minute task.

- [ ] **4. Add one-click "Load Example" button**  
  On the landing page, add a button that pre-fills the query field with "lung adenocarcinoma overall survival" and auto-submits. Satisfies NAR "easy loading mechanism" requirement.

- [ ] **5. Add sample output links in Help page**  
  Run the example query on the live server. Save the permalink. Add it to `HelpPage.tsx` as a clickable link showing sample output.

- [ ] **6. Verify no tracking cookies**  
  Audit `frontend/src/` for any analytics imports (Google Analytics, Mixpanel, etc.). Check `Caddyfile` for logging settings. Confirm `CookieConsent.tsx` covers all cookies used.

- [ ] **7. Write biological use case study**  
  Run a real analysis (suggested: lung adenocarcinoma overall survival). Document: query used, datasets found, top genes, KM curves, interpretation of HR, biological significance. This becomes a section of the manuscript.

- [ ] **8. Create graphical abstract**  
  Single-figure workflow: user types NL query → tool searches GEO → downloads + parses expression matrices → Cox regression per dataset → cross-cohort ranking → KM curves + forest plot output. Use tools like BioRender or draw.io.

- [ ] **9. Write NAR manuscript**  
  Download NAR Word/LaTeX template. Sections needed: Abstract (with URL), Introduction, Methods (input/processing/output), Results (use case with biological insight), Comparison with existing methods, Conclusion. Typical length: 4-5 journal pages.

- [ ] **10. Submit proposal to nar.bihealth.de by December 20, 2026**  
  One-page summary including: input/output description, 2-4 keywords, affirmative free-access statement, list of similar tools, PubMed IDs of related publications.

---

## How to Use This Skill

- Invoke as `/nar-submission` to review current status.
- To mark a task complete: ask Claude to update the checkbox from `[ ]` to `[x]` and change the table status symbol from ❌/⚠️ to ✅.
- To update a partial item: describe what was done and Claude will update the notes column.
- This file persists across sessions — always reflects the real current state of the submission.

---

## Proposal Affirmative Statement (required verbatim)

> "This website is free and open to all users and there is no login requirement."

Already displayed on the app landing page. Must also appear in the one-page proposal and in the manuscript body.

## Similar Tools to List in Cover Letter

| Tool | URL | Limitation vs GEO Survival Analysis |
|------|-----|--------------------------------------|
| KMplot | kmplot.com | TCGA + curated data only; no cross-cohort meta-analysis; no NL input |
| GEPIA2 | gepia2.cancer-pku.cn | TCGA + GTEx only; no meta-analysis |
| OncoLnc | oncolnc.org | TCGA only; limited cancer types |
| SurvExpress | bioinformatica.mty.itesm.mx/survexpress | Upload-only; no GEO search |
| TIMER2 | timer.cistrome.org | Immune focus; no free-text GEO search |
| cBioPortal | cbioportal.org | Clinical data portal; no survival meta-analysis across GEO |
