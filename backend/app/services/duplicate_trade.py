"""Local cross-case comparisons of current source-derived commercial invoices."""

import hashlib
import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.integrations.risk.contracts import Category, ProviderInput, ProviderResult
from app.models.documents import DocumentProcessingRun, DocumentVersion
from app.models.domain import CaseDocument, TradeCase
from app.rules import Subject
from app.services.comparisons import normalized_identifier, normalized_party
from app.services.fact_resolver import build_case_evidence, resolve

FIELDS = ("invoice_number", "seller", "buyer", "total_amount", "purchase_order_reference")


def load_current_corpora(session: Session) -> list[dict]:
    cases = session.scalars(
        select(TradeCase)
        .order_by(TradeCase.case_id)
        .options(
            selectinload(TradeCase.documents)
            .selectinload(CaseDocument.versions)
            .selectinload(DocumentVersion.pages),
            selectinload(TradeCase.documents)
            .selectinload(CaseDocument.versions)
            .selectinload(DocumentVersion.runs)
            .selectinload(DocumentProcessingRun.facts),
            selectinload(TradeCase.parties),
        )
        .execution_options(populate_existing=True)
    ).all()
    return [build_case_evidence(c, c.documents) for c in cases]


def invoice_profiles(corpora: list[dict], threshold: Decimal) -> list[dict]:
    profiles = []
    for corpus in corpora:
        for document in corpus["documents"]:
            if document["document_type"] != "COMMERCIAL_INVOICE":
                continue
            single = {**corpus, "documents": [document]}
            values, evidence, unresolved = {}, [], []
            for field in FIELDS:
                resolution = resolve(
                    single,
                    Subject(
                        document_type="COMMERCIAL_INVOICE", fields=(field,), role="Invoice " + field
                    ),
                    threshold,
                )
                if resolution.state == "READY":
                    values[field] = resolution.evidence["comparison_value"]
                    evidence.append(resolution.evidence)
                else:
                    unresolved.append(field)
            canonical = {}
            for field in ("seller", "buyer", "invoice_number"):
                value = values.get(field)
                if isinstance(value, str):
                    canonical[field] = (
                        normalized_identifier(value)
                        if field == "invoice_number"
                        else normalized_party(value)
                    )
            money = values.get("total_amount")
            if isinstance(money, dict):
                canonical.update(
                    {
                        "amount": str(Decimal(money["amount"]).normalize()),
                        "currency": money["currency"],
                    }
                )
            if values.get("purchase_order_reference"):
                canonical["purchase_order_reference"] = normalized_identifier(
                    values["purchase_order_reference"]
                )
            essential = {"invoice_number", "seller", "buyer", "amount", "currency"}
            fingerprint = (
                hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
                if essential.issubset(canonical)
                else None
            )
            profiles.append(
                {
                    "case_id": corpus["case_id"],
                    "document_id": document["document_id"],
                    "version_id": document["document_version_id"],
                    "sha256": document["sha256"],
                    "values": canonical,
                    "evidence": evidence,
                    "unresolved": unresolved,
                    "commercial_fingerprint": fingerprint,
                }
            )
    return profiles


def duplicate_candidates(current: dict, profiles: list[dict]) -> list[dict]:
    results = []
    for candidate in profiles:
        # Multiple versions or extraction attempts of the same document aren't financing events.
        if (
            candidate["case_id"] == current["case_id"]
            or candidate["document_id"] == current["document_id"]
        ):
            continue
        left, right = current["values"], candidate["values"]
        matched = [k for k in left.keys() & right.keys() if left[k] == right[k]]
        different = [k for k in left.keys() & right.keys() if left[k] != right[k]]
        kind, score = None, None
        if current["sha256"] == candidate["sha256"]:
            kind, score = "EXACT_FILE_DUPLICATE", "1.00"
            matched.append("sha256")
        elif current.get("commercial_fingerprint") and current[
            "commercial_fingerprint"
        ] == candidate.get("commercial_fingerprint"):
            kind, score = "DOCUMENT_DUPLICATE_CANDIDATE", "0.97"
            matched.append("commercial_fingerprint")
        elif {"invoice_number", "seller", "buyer", "currency", "amount"}.issubset(matched):
            kind, score = "DOCUMENT_DUPLICATE_CANDIDATE", "0.95"
        elif {"invoice_number", "seller", "buyer"}.issubset(matched):
            kind, score = "DOCUMENT_DUPLICATE_CANDIDATE", "0.80"
        elif {"invoice_number", "seller", "currency", "amount"}.issubset(matched):
            kind, score = "DOCUMENT_DUPLICATE_CANDIDATE", "0.85"
        # Same seller/amount without invoice identity is not a candidate.
        if kind:
            results.append(
                {
                    "candidate_case_id": candidate["case_id"],
                    "candidate_document_id": candidate["document_id"],
                    "candidate_version_id": candidate["version_id"],
                    "kind": kind,
                    "score": score,
                    "score_basis": "Configured deterministic evidence grade, not probability",
                    "matched_fields": sorted(matched),
                    "different_fields": sorted(different),
                    "candidate_evidence": candidate["evidence"],
                    "financing_status": "NOT_CHECKED",
                    "financing_reason": "No independent financing/presentation event ledger exists",
                }
            )
    return results


class LocalDuplicateTradeProvider:
    category = Category.DUPLICATE
    name = "LOCAL_DUPLICATE_TRADE"
    version = "duplicate-v1"

    def __init__(self, profiles):
        self.profiles = profiles

    def snapshot(self):
        return {
            "category": self.category,
            "name": self.name,
            "version": self.version,
            "scope": "Current cross-case MySQL invoice evidence",
            "profiles": self.profiles,
        }

    def check(self, subject: ProviderInput):
        current = subject.trade.get("invoice_profile")
        if not current:
            return ProviderResult(status="NOT_APPLICABLE", reason="No current commercial invoice")
        candidates = duplicate_candidates(current, self.profiles)
        if candidates:
            return ProviderResult(
                status="POTENTIAL_MATCH",
                reason="Explainable cross-case invoice candidate; not proof of financing or fraud",
                details={"candidates": candidates},
            )
        if not {"invoice_number", "seller", "buyer", "currency", "amount"}.issubset(
            current["values"]
        ):
            return ProviderResult(
                status="INSUFFICIENT_DATA",
                reason="Incomplete current invoice identity; exact hash search found no duplicate",
                details={"candidates": []},
            )
        return ProviderResult(
            status="CLEAR",
            reason="No candidate among current stored invoices",
            details={
                "candidates": [],
                "financing_status": "NOT_CHECKED",
                "financing_reason": "No independent financing event ledger exists",
            },
        )
