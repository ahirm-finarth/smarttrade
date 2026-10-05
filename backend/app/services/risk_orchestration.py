"""Auditable risk orchestration: provider facts → versioned policy → findings."""

from collections import Counter
from datetime import timedelta
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.integrations.risk.contracts import (
    Category,
    ProviderInput,
    ProviderRegistry,
    ProviderResult,
)
from app.integrations.risk.synthetic import (
    SyntheticCountryRiskProvider,
    SyntheticPortRiskProvider,
    SyntheticScreeningProvider,
    SyntheticVesselRiskProvider,
    UnavailableSyntheticProvider,
    load_references,
)
from app.integrations.risk.trade_policy import (
    SyntheticFairValueProvider,
    SyntheticGoodsRiskProvider,
)
from app.models.domain import TradeCase, now
from app.models.risk import ProviderCheck, RiskFinding, RiskRuleExecution, RiskRun
from app.rules import Subject
from app.rules.risk import RULES, RULESET_VERSION, interpret
from app.services.comparisons import normalized_party
from app.services.documents import DocumentConflict
from app.services.duplicate_trade import (
    LocalDuplicateTradeProvider,
    invoice_profiles,
    load_current_corpora,
)
from app.services.examination_engine import fingerprint
from app.services.fact_resolver import case_by_id, resolve


class RiskRunNotFound(Exception):
    pass


def default_registry(profiles):
    try:
        records = load_references()
        reference_providers = [
            SyntheticScreeningProvider(records),
            SyntheticCountryRiskProvider(records),
            SyntheticPortRiskProvider(records),
            SyntheticVesselRiskProvider(records),
        ]
    except (OSError, ValidationError, UnicodeError):
        reference_providers = [
            UnavailableSyntheticProvider(category)
            for category in (Category.SCREENING, Category.COUNTRY, Category.PORT, Category.VESSEL)
        ]
    return ProviderRegistry(
        [
            *reference_providers,
            LocalDuplicateTradeProvider(profiles),
            SyntheticGoodsRiskProvider(),
            SyntheticFairValueProvider(),
        ]
    )


def operational_parties(case):
    return [
        {"id": p.id, "role": p.party_role, "name": p.party_name, "country": p.country}
        for p in sorted(case.parties, key=lambda p: p.id)
    ]


def plans(case, corpus, profiles, threshold):
    result = []

    def add(category, key, subject, unavailable=None):
        result.append(
            {"category": category, "key": key, "input": subject, "unavailable": unavailable}
        )

    for party in operational_parties(case):
        if party["role"] and party["role"].casefold() == "vessel":
            continue
        evidence = []
        if party["name"]:
            for d in corpus["documents"]:
                for f in d["facts"]:
                    if f["field_name"] not in {
                        "seller",
                        "buyer",
                        "beneficiary",
                        "applicant",
                        "exporter",
                        "drawer",
                        "drawee",
                        "consignee",
                        "contractor",
                        "employer",
                    }:
                        continue
                    resolution = resolve(
                        {**corpus, "documents": [d]},
                        Subject(
                            document_type=d["document_type"],
                            fields=(f["field_name"],),
                            role=party["role"] or "Case party",
                        ),
                        threshold,
                    )
                    if resolution.state == "READY" and normalized_party(
                        str(f["normalized_value"])
                    ) == normalized_party(party["name"]):
                        evidence.append(resolution.evidence)
        add(
            Category.SCREENING,
            f"party-{party['id']}",
            ProviderInput(
                subject_type="party",
                subject=party["name"],
                role=party["role"],
                country=party["country"],
                party_id=party["id"],
                evidence=evidence,
            ),
            "Party name not supplied" if not party["name"] else None,
        )
    if not any(p["category"] == Category.SCREENING for p in result):
        add(Category.SCREENING, "party-none", ProviderInput(subject_type="party"))
    for country in sorted({p["country"] for p in operational_parties(case) if p["country"]}):
        add(
            Category.COUNTRY,
            "country-" + country,
            ProviderInput(
                subject_type="country",
                subject=country,
                trade={
                    "party_ids": [
                        p["id"] for p in operational_parties(case) if p["country"] == country
                    ]
                },
            ),
        )
    if not any(p["category"] == Category.COUNTRY for p in result):
        add(Category.COUNTRY, "country-none", ProviderInput(subject_type="country"))

    def field(category, key, kind, name):
        r = resolve(
            corpus,
            Subject(document_type=kind, fields=(name,), role=name.replace("_", " ")),
            threshold,
        )
        e = r.evidence
        add(
            category,
            key,
            ProviderInput(
                subject_type=category,
                subject=str(e["comparison_value"]) if r.state == "READY" else None,
                evidence=[e] if e else [],
            ),
            r.reason if r.state not in {"READY", "MISSING"} else None,
        )

    for name in ("port_of_loading", "port_of_discharge"):
        field(Category.PORT, name, "BILL_OF_LADING", name)
    field(Category.VESSEL, "vessel", "BILL_OF_LADING", "vessel_name")
    field(Category.COUNTRY, "origin-country", "CERTIFICATE_OF_ORIGIN", "country_of_origin")
    invoice_docs = [d for d in corpus["documents"] if d["document_type"] == "COMMERCIAL_INVOICE"]
    if not invoice_docs:
        for category in (Category.DUPLICATE, Category.GOODS, Category.FAIR_VALUE):
            add(category, category + "-none", ProviderInput(subject_type="invoice"))
    for d in invoice_docs:
        profile = next(p for p in profiles if p["document_id"] == d["document_id"])
        single = {**corpus, "documents": [d]}
        amount = {}
        evidence = []
        unavailable = []
        for name in ("goods_description", "unit_price", "quantity", "total_amount"):
            r = resolve(
                single,
                Subject(
                    document_type="COMMERCIAL_INVOICE", fields=(name,), role=name.replace("_", " ")
                ),
                threshold,
            )
            if r.state == "READY":
                amount[name] = r.evidence["comparison_value"]
                evidence.append(r.evidence)
            elif r.state not in {"MISSING"}:
                unavailable.append(r.reason)
        add(
            Category.DUPLICATE,
            f"duplicate-{d['document_id']}",
            ProviderInput(
                subject_type="invoice",
                subject=profile["values"].get("invoice_number"),
                evidence=profile["evidence"],
                trade={"invoice_profile": profile},
            ),
        )
        for category in (Category.GOODS, Category.FAIR_VALUE):
            add(
                category,
                f"{category}-{d['document_id']}",
                ProviderInput(
                    subject_type="goods",
                    subject=amount.get("goods_description"),
                    evidence=evidence,
                    trade=amount,
                ),
                "; ".join(sorted(set(unavailable))) if unavailable else None,
            )
    return result


def risk_context(session, settings, case_id, registry=None):
    corpora = load_current_corpora(session)
    case = case_by_id(session, case_id)
    corpus = next(c for c in corpora if c["case_id"] == case_id)
    profiles = invoice_profiles(corpora, settings.examination_min_confidence)
    registry = registry or default_registry(profiles)
    items = plans(case, corpus, profiles, settings.examination_min_confidence)
    snapshot = {
        "case_id": case_id,
        "parties": operational_parties(case),
        "evidence": corpus,
        "provider_configuration": registry.snapshot(),
        "rules": [r.model_dump(mode="json") for r in RULES],
        "confidence_threshold": str(settings.examination_min_confidence),
        "cross_case_invoice_profiles": profiles,
    }
    return case, registry, items, snapshot


def run_risk_checks(
    session: Session,
    settings: Settings,
    case_id: str,
    request_id: str | None = None,
    registry: ProviderRegistry | None = None,
):
    case = case_by_id(session, case_id)
    session.scalar(select(TradeCase).where(TradeCase.id == case.id).with_for_update())
    key = request_id or str(uuid4())
    repeated = session.scalar(
        select(RiskRun).where(RiskRun.case_pk == case.id, RiskRun.request_id == key)
    )
    if repeated:
        session.commit()
        return get_risk_run(session, repeated.id)
    latest = session.scalar(
        select(RiskRun)
        .where(RiskRun.case_pk == case.id)
        .order_by(RiskRun.run_number.desc())
        .limit(1)
    )
    if latest and latest.status == "RUNNING":
        if latest.started_at > now() - timedelta(minutes=5):
            session.rollback()
            raise DocumentConflict("Risk checks are already running")
        latest.status = "FAILED"
        latest.completed_at = now()
        latest.error_message = "Previous risk worker expired"
    case, registry, items, snapshot = risk_context(session, settings, case_id, registry)
    run = RiskRun(
        case_pk=case.id,
        run_number=latest.run_number + 1 if latest else 1,
        request_id=key,
        ruleset_version=RULESET_VERSION,
        provider_set="synthetic-and-local-v1",
        status="RUNNING",
        input_snapshot_json=snapshot,
        input_fingerprint=fingerprint(snapshot),
    )
    session.add(run)
    session.commit()
    run_id = run.id
    try:
        statuses = Counter()
        categories = Counter()
        severities = Counter()
        finding_count = 0
        for item in items:
            category = item["category"]
            subject = item["input"]
            started = now()
            provider = registry.providers.get(category)
            try:
                if item["unavailable"]:
                    result = ProviderResult(status="INSUFFICIENT_DATA", reason=item["unavailable"])
                elif provider is None:
                    raise ValueError("Provider not configured")
                else:
                    # Revalidate even if a replaceable provider returns an untyped payload.
                    raw = provider.check(subject)
                    result = ProviderResult.model_validate(
                        raw.model_dump() if isinstance(raw, ProviderResult) else raw
                    )
            except Exception:
                result = ProviderResult(
                    status="PROVIDER_ERROR",
                    reason="Provider failed; private diagnostics suppressed",
                )
            check = ProviderCheck(
                risk_run_pk=run.id,
                case_pk=case.id,
                check_key=item["key"],
                provider_type=category,
                provider_name=provider.name if provider else "UNAVAILABLE_" + category.upper(),
                provider_version=provider.version if provider else "none",
                status=result.status,
                input_json=subject.model_dump(mode="json"),
                result_json=result.model_dump(mode="json"),
                started_at=started,
                completed_at=now(),
            )
            session.add(check)
            session.flush()
            statuses[result.status] += 1
            categories[category] += 1
            for rule in (r for r in RULES if r.category == category):
                output = interpret(rule, result)
                execution = RiskRuleExecution(
                    risk_run_pk=run.id,
                    provider_check_pk=check.id,
                    rule_id=rule.id,
                    rule_version=rule.version,
                    status=output["status"],
                    rule_snapshot_json=rule.model_dump(mode="json"),
                    input_json={"subject": check.input_json, "provider": check.result_json},
                    output_json=output,
                )
                session.add(execution)
                session.flush()
                for finding in output["findings"]:
                    candidate = finding.get("candidate")
                    subject_value = subject.subject or "Unspecified"
                    if candidate:
                        subject_value += (
                            f" → {candidate['candidate_case_id']} / "
                            f"{candidate['candidate_document_id']}"
                        )
                    session.add(
                        RiskFinding(
                            case_pk=case.id,
                            risk_run_pk=run.id,
                            provider_check_pk=check.id,
                            rule_execution_pk=execution.id,
                            finding_type=finding["finding_type"],
                            category=category,
                            title=finding["finding_type"].replace("_", " ").capitalize(),
                            description=finding["description"],
                            severity=rule.severity,
                            rule_id=rule.id,
                            rule_version=rule.version,
                            subject_type=subject.subject_type,
                            subject_value=subject_value[:255],
                            evidence_json={
                                "subject": check.input_json,
                                "provider": {
                                    "name": check.provider_name,
                                    "version": check.provider_version,
                                    "result": check.result_json,
                                },
                                "rule": execution.rule_snapshot_json,
                                "candidate": candidate,
                            },
                        )
                    )
                    severities[rule.severity] += 1
                    finding_count += 1
        run.status = (
            "PARTIAL"
            if statuses["PROVIDER_ERROR"] or statuses["INSUFFICIENT_DATA"]
            else "COMPLETED"
        )
        run.summary_json = {
            "checks": dict(categories),
            "results_by_status": dict(statuses),
            "findings": finding_count,
            "findings_by_severity": dict(severities),
            "rules_executed": sum(1 for i in items for r in RULES if r.category == i["category"]),
            "synthetic": True,
            "decision_computed": False,
        }
        run.completed_at = now()
        session.commit()
    except Exception:
        session.rollback()
        run = session.get(RiskRun, run_id)
        run.status = "FAILED"
        run.completed_at = now()
        run.error_message = (
            "Risk persistence failed; partial outputs rolled back. Retry explicitly."
        )
        session.commit()
    return get_risk_run(session, run_id)


def get_risk_run(session, run_id):
    run = session.scalar(
        select(RiskRun)
        .where(RiskRun.id == run_id)
        .options(
            selectinload(RiskRun.checks),
            selectinload(RiskRun.executions),
            selectinload(RiskRun.findings),
        )
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise RiskRunNotFound
    return run


def risk_history(session, case_id):
    case = case_by_id(session, case_id)
    return session.scalars(
        select(RiskRun).where(RiskRun.case_pk == case.id).order_by(RiskRun.run_number.desc())
    ).all()


def risk_inputs_current(session, settings, run):
    try:
        case = session.get(TradeCase, run.case_pk)
        _, _, _, snapshot = risk_context(session, settings, case.case_id)
        return fingerprint(snapshot) == run.input_fingerprint
    except (ValueError, KeyError):
        return False
