"""Bundled gene -> therapy evidence from open knowledge bases (CIViC, DGIdb).

Purpose: ground the AI "therapeutic directions" rationale (Oncologist Mode) in
REAL, citable biomarker -> drug associations rather than letting the model
speculate. We surface documented evidence for the patient's risk-driving genes;
we never recommend a therapy.

Positioning guardrail (clinical-positioning skill §2): this is hypothesis-
generating prognostic context. Predictive (drug-response) evidence from CIViC is
shown WITH its source so a clinician can judge it — it is not the app's claim.

Data:
  * CIViC ClinicalEvidenceSummaries (CC0) — Predictive / Prognostic evidence,
    with significance (sensitivity/resistance/outcome), direction, level, URL.
  * DGIdb interactions (open) — anti-neoplastic gene/drug interactions.

Both dumps are downloaded once into `data/therapy_sources/` and normalised into
a compact `data/therapy_evidence.json` keyed by uppercase gene symbol. The
service loads that JSON at startup; lookups are an in-memory dict (async-safe,
offline). If the index is absent, lookups simply return nothing and the endpoint
reports "no documented associations" — it never fabricates.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_INDEX_PATH = _DATA_DIR / "therapy_evidence.json"
_CIVIC_TSV = _DATA_DIR / "therapy_sources" / "civic_clinical_evidence.tsv"
_DGIDB_TSV = _DATA_DIR / "therapy_sources" / "dgidb_interactions.tsv"

# Caps keep the bundled index small and lookups focused.
_MAX_CIVIC_PER_GENE = 10
_MAX_DGIDB_PER_GENE = 8
_RELEVANT_CIVIC_TYPES = {"Predictive", "Prognostic"}


_DISEASE_STOPWORDS = frozenset({
    "cancer", "cancers", "carcinoma", "tumor", "tumour", "tumors", "tumours",
    "neoplasm", "neoplasms", "disease", "of", "the", "and", "not", "otherwise",
    "specified", "adenocarcinoma",
})


def _disease_tokens(text: str) -> set:
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in _DISEASE_STOPWORDS and len(w) >= 4}


def _disease_matches(disease: Optional[str], cancer_type: Optional[str]) -> Optional[bool]:
    """Best-effort, non-authoritative check that a CIViC evidence row's
    `disease` (e.g. "Acute Myeloid Leukemia") is about the same cancer as the
    app's current `cancer_type` (e.g. "breast"). Returns None (unknown, not a
    match claim) when either side is missing — never assume a match. This is
    a coarse keyword-overlap heuristic, not an ontology lookup: good enough to
    catch a flatly different cancer type (AML evidence surfaced for a breast
    case), not to arbitrate borderline subtype naming."""
    if not disease or not cancer_type:
        return None
    a, b = _disease_tokens(disease), _disease_tokens(cancer_type)
    if not a or not b:
        return None
    return bool(a & b)


def _gene_from_molecular_profile(profile: str) -> Optional[str]:
    """CIViC molecular profiles lead with the gene symbol, e.g. 'EGFR L858R',
    'ERBB2 Amplification'. Take the leading symbol-like token."""
    if not profile:
        return None
    token = profile.strip().split()[0].upper()
    # Skip multi-gene fusions / complex profiles we can't attribute cleanly.
    if not token or any(c in token for c in (":", "-", "(", ")")):
        return None
    return token if token.replace("_", "").isalnum() else None


class TherapyEvidenceService:
    """Loads and serves the bundled gene -> therapy evidence index."""

    def __init__(self) -> None:
        # gene_symbol -> {"civic": [...], "dgidb": [...]}
        self._index: Dict[str, Dict[str, list]] = {}

    # ---------- loading ----------

    def load(self) -> int:
        """Load the compact index from disk (building it from TSVs if needed).
        Returns the number of genes indexed."""
        if _INDEX_PATH.exists():
            try:
                self._index = json.loads(_INDEX_PATH.read_text())
            except (OSError, ValueError) as e:
                logger.warning("Failed to read therapy evidence index: %s", e)
                self._index = {}
        elif _CIVIC_TSV.exists() or _DGIDB_TSV.exists():
            self._index = self.build_index()
            self.save()
        else:
            logger.info("No therapy evidence sources found; therapy rationale will report none.")
            self._index = {}
        if self._index:
            logger.info("Therapy evidence index ready (%d genes)", len(self._index))
        return len(self._index)

    def has_data(self) -> bool:
        return bool(self._index)

    def save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _INDEX_PATH.write_text(json.dumps(self._index, separators=(",", ":")))

    # ---------- lookup ----------

    def lookup(
        self, genes: List[str], max_total: int = 40, cancer_type: Optional[str] = None
    ) -> List[dict]:
        """Flatten documented evidence for `genes` (case-insensitive) into a list
        of attributed records, capped to `max_total`. Empty when nothing known.

        Each record carries `disease_matches_current_cancer`: True/False when
        the evidence's own disease can be compared against `cancer_type`
        (CIViC only — DGIdb interactions carry no disease field), else None
        (unknown; never claimed as a match). Within each gene, non-matching
        evidence (documented for a clearly different cancer type, e.g. an
        AML-specific drug surfaced for a breast-cancer patient) sorts after
        matching/unknown evidence so capping to `max_total` doesn't crowd out
        genuinely relevant rows — it is never dropped outright, since GEO
        Survival Analysis never fabricates OR hides documented evidence."""
        out: List[dict] = []
        for gene in genes:
            entry = self._index.get(gene.upper())
            if not entry:
                continue
            gene_recs: List[dict] = []
            for rec in entry.get("civic", []):
                match = _disease_matches(rec.get("disease"), cancer_type)
                gene_recs.append(
                    {"gene": gene.upper(), "source": "CIViC", "disease_matches_current_cancer": match, **rec}
                )
            for rec in entry.get("dgidb", []):
                gene_recs.append(
                    {"gene": gene.upper(), "source": "DGIdb", "disease_matches_current_cancer": None, **rec}
                )
            gene_recs.sort(key=lambda r: r["disease_matches_current_cancer"] is False)
            out.extend(gene_recs)
            if len(out) >= max_total:
                break
        return out[:max_total]

    # ---------- build (offline / first-run) ----------

    @classmethod
    def build_index(
        cls, civic_path: Path = _CIVIC_TSV, dgidb_path: Path = _DGIDB_TSV
    ) -> Dict[str, Dict[str, list]]:
        index: Dict[str, Dict[str, list]] = {}

        def bucket(gene: str) -> Dict[str, list]:
            return index.setdefault(gene, {"civic": [], "dgidb": []})

        if civic_path.exists():
            with civic_path.open(newline="") as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    if row.get("evidence_type") not in _RELEVANT_CIVIC_TYPES:
                        continue
                    therapies = (row.get("therapies") or "").strip()
                    if not therapies:
                        continue
                    gene = _gene_from_molecular_profile(row.get("molecular_profile", ""))
                    if not gene:
                        continue
                    civ = bucket(gene)["civic"]
                    if len(civ) >= _MAX_CIVIC_PER_GENE:
                        continue
                    civ.append(
                        {
                            "drug": therapies,
                            "evidence_type": row.get("evidence_type"),
                            "significance": row.get("significance") or None,
                            "direction": row.get("evidence_direction") or None,
                            "evidence_level": row.get("evidence_level") or None,
                            "disease": row.get("disease") or None,
                            "url": row.get("evidence_civic_url") or None,
                        }
                    )

        if dgidb_path.exists():
            with dgidb_path.open(newline="") as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    if (row.get("anti_neoplastic") or "").lower() != "true":
                        continue
                    gene = (row.get("gene_name") or "").strip().upper()
                    drug = (row.get("drug_name") or "").strip()
                    if not gene or not drug:
                        continue
                    dg = bucket(gene)["dgidb"]
                    if len(dg) >= _MAX_DGIDB_PER_GENE:
                        continue
                    if any(r["drug"].upper() == drug.upper() for r in dg):
                        continue  # dedupe by drug
                    itype = row.get("interaction_type") or ""
                    dg.append(
                        {
                            "drug": drug,
                            "interaction_type": itype if itype and itype != "NULL" else None,
                            "approved": (row.get("approved") or "").lower() == "true",
                            "source_db": row.get("interaction_source_db_name") or None,
                        }
                    )

        # Drop genes that ended up empty.
        return {g: e for g, e in index.items() if e["civic"] or e["dgidb"]}


if __name__ == "__main__":  # build the bundled index: `python -m app.services.therapy_evidence_service`
    idx = TherapyEvidenceService.build_index()
    svc = TherapyEvidenceService()
    svc._index = idx
    svc.save()
    print(f"Wrote {_INDEX_PATH} with {len(idx)} genes")
