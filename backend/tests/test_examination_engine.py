import copy
import hashlib
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.models import Base
from app.models.documents import DocumentPage, DocumentProcessingRun, DocumentVersion, ExtractedFact
from app.models.domain import CaseDocument, TradeCase
from app.models.examination import ExaminationRun, RuleExecution
from app.rules import GUARANTEE, IMPORT, load_rules
from app.schemas.intelligence import EXTRACTION_FIELDS
from app.services.examination_engine import examination_is_current, get_examination, run_examination
from app.services.normalization import normalize_value


@pytest.fixture(name="database")
def database():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def add_document(session, case, kind, values, document=None, confidence="0.99"):
    if document is None:
        document = CaseDocument(case_pk=case.id, source_key=str(uuid4()), file_name=kind + ".pdf")
        session.add(document)
        session.flush()
    number = max((v.version_number for v in document.versions), default=0) + 1
    text = "Synthetic test source\n" + "\n".join(f"{name}\n{raw}" for name, raw in values.items())
    version = DocumentVersion(
        document_pk=document.id,
        case_pk=case.id,
        version_number=number,
        original_filename=kind + ".pdf",
        storage_path="unit-test-only",
        mime_type="application/pdf",
        file_size_bytes=len(text),
        sha256=hashlib.sha256((text + str(uuid4())).encode()).hexdigest(),
        status="COMPLETED",
        page_count=1,
    )
    session.add(version)
    session.flush()
    session.add(
        DocumentPage(
            document_version_pk=version.id,
            page_number=1,
            text_content=text,
            text_length=len(text),
            extraction_method="NATIVE_TEXT",
            needs_review=False,
        )
    )
    run = DocumentProcessingRun(
        document_version_pk=version.id,
        run_number=1,
        status="COMPLETED",
        document_type=kind,
        classification_confidence=Decimal("0.99"),
        metadata_json={"input": "source_pdf_pages_only"},
    )
    session.add(run)
    session.flush()
    for field, raw in values.items():
        normal = normalize_value(EXTRACTION_FIELDS[kind][field], raw)
        session.add(
            ExtractedFact(
                processing_run_pk=run.id,
                field_name=field,
                raw_value=raw,
                normalized_json=normal,
                normalized_value=str(normal),
                page_number=1,
                source_text=f"{field}\n{raw}",
                confidence=Decimal(confidence),
                evidence_status="SUPPORTED",
            )
        )
    session.commit()
    return document


def import_case(session, *, amount="USD 100.00", quantity="10 PCS", invoice_quantity=True):
    case = TradeCase(case_id="UNIT-IMP", product_playbook=IMPORT)
    session.add(case)
    session.commit()
    add_document(
        session,
        case,
        "LETTER_OF_CREDIT",
        {
            "amount": "USD 100.00",
            "quantity": "10 PIECES",
            "beneficiary": "ABC Exports Private Limited",
            "applicant": "Buyer LLC",
            "goods_description": "Machine parts",
            "latest_shipment_date": "2026-03-15",
            "port_of_loading": "Port A",
            "port_of_discharge": "Port B",
        },
    )
    invoice = {
        "total_amount": amount,
        "seller": "ABC Exports Pvt. Ltd.",
        "buyer": "Buyer LLC",
        "goods_description": "Machine parts",
        "invoice_number": "INV-001",
    }
    if invoice_quantity:
        invoice["quantity"] = quantity
    add_document(session, case, "COMMERCIAL_INVOICE", invoice)
    add_document(session, case, "PACKING_LIST", {"invoice_number": "INV 001", "quantity": quantity})
    add_document(
        session,
        case,
        "BILL_OF_LADING",
        {
            "shipment_date": "2026-03-14",
            "port_of_loading": "Port A",
            "port_of_discharge": "Port B",
            "consignee": "Buyer LLC",
        },
    )
    return case


def test_clean_case_and_provenance_backed_relations(database):
    with Session(database) as s:
        case = import_case(s)
        run = run_examination(s, Settings(_env_file=None), case.case_id)
        assert run.status == "CLEAN" and not run.findings
        assert run.summary_json["matched"] == len(load_rules(IMPORT))
        assert run.relations and all(r.source_fact_pk != r.target_fact_pk for r in run.relations)
        execution = next(e for e in run.executions if e.rule_id == "DOC-LC-AMOUNT-001")
        assert (
            execution.rule_version == 1
            and execution.rule_snapshot_json["parameters"]["tolerance_percent"] == "0"
        )
        for side in ("expected", "observed"):
            evidence = execution.input_json[side]["evidence"]
            assert evidence["fact_id"] and evidence["page_number"] == 1 and evidence["source_text"]


def test_amount_and_quantity_mismatches_generate_actual_findings(database):
    with Session(database) as s:
        case = import_case(s, amount="USD 106.00", quantity="11 PCS")
        run = run_examination(s, Settings(_env_file=None), case.case_id)
        assert run.status == "DISCREPANCIES_FOUND"
        assert sorted(f.finding_type for f in run.findings) == [
            "AMOUNT_MISMATCH",
            "QUANTITY_MISMATCH",
            "QUANTITY_MISMATCH",
        ]
        finding = next(f for f in run.findings if f.finding_type == "AMOUNT_MISMATCH")
        assert finding.expected_json["normalized_value"]["amount"] == "100.00"
        assert finding.observed_json["normalized_value"]["amount"] == "106.00"
        assert finding.expected_fact_pk != finding.observed_fact_pk


def test_missing_extraction_is_incomplete_not_a_discrepancy(database):
    with Session(database) as s:
        case = import_case(s, invoice_quantity=False)
        run = run_examination(s, Settings(_env_file=None), case.case_id)
        assert run.status == "INCOMPLETE_EXAMINATION" and not run.findings
        assert run.summary_json["results_by_status"]["MISSING_RIGHT"] == 1
        assert run.summary_json["results_by_status"]["MISSING_LEFT"] == 1
        # Packing-list own identifier was not extracted; no reference mismatch is invented.
        assert not any(f.finding_type == "INVOICE_REFERENCE_MISMATCH" for f in run.findings)


def test_low_confidence_requires_review(database):
    with Session(database) as s:
        case = import_case(s)
        fact = s.scalar(select(ExtractedFact).where(ExtractedFact.field_name == "total_amount"))
        fact.confidence = Decimal("0.6")
        s.commit()
        run = run_examination(s, Settings(_env_file=None), case.case_id)
        assert run.status == "INCOMPLETE_EXAMINATION" and not run.findings
        assert run.summary_json["results_by_status"]["NEEDS_REVIEW"] == 2


def test_rerun_and_new_source_keep_historical_inputs_immutable(database):
    with Session(database) as s:
        case = import_case(s)
        first = run_examination(s, Settings(_env_file=None), case.case_id)
        original = copy.deepcopy(first.input_snapshot_json)
        execution_inputs = [copy.deepcopy(e.input_json) for e in first.executions]
        assert examination_is_current(s, first)
        assert not examination_is_current(
            s, first, Settings(_env_file=None, examination_min_confidence="0.95")
        )
        doc = s.scalar(
            select(CaseDocument).where(CaseDocument.file_name == "COMMERCIAL_INVOICE.pdf")
        )
        add_document(s, case, "COMMERCIAL_INVOICE", {"total_amount": "USD 106.00"}, document=doc)
        assert not examination_is_current(s, first)
        second = run_examination(s, Settings(_env_file=None), case.case_id)
        assert second.id != first.id and second.run_number == first.run_number + 1
        old = get_examination(s, first.id)
        assert (
            old.input_snapshot_json == original
            and [e.input_json for e in old.executions] == execution_inputs
        )
        assert old.status == "CLEAN" and second.status == "DISCREPANCIES_FOUND"


def test_request_id_deduplicates_only_the_same_submission(database):
    with Session(database) as s:
        case = import_case(s)
        key = str(uuid4())
        first = run_examination(s, Settings(_env_file=None), case.case_id, key)
        assert run_examination(s, Settings(_env_file=None), case.case_id, key).id == first.id
        second = run_examination(s, Settings(_env_file=None), case.case_id, str(uuid4()))
        assert second.id != first.id
        assert s.scalar(select(func.count()).select_from(ExaminationRun)) == 2
        assert len(second.executions) == len(first.executions)


def test_failed_execution_rolls_back_partial_outputs_and_keeps_failed_run(database, monkeypatch):
    with Session(database) as s:
        case = import_case(s)

        def fail(*args):
            raise RuntimeError("Private internal detail must not appear")

        monkeypatch.setattr("app.services.examination_engine.compare_resolutions", fail)
        run = run_examination(s, Settings(_env_file=None), case.case_id)
        assert run.status == "FAILED" and "Private" not in run.error_message
        assert not run.executions and not run.findings
        assert s.scalar(select(func.count()).select_from(RuleExecution)) == 0


def test_required_statement_is_not_inferred_from_missing_extraction(database):
    with Session(database) as s:
        case = TradeCase(case_id="UNIT-BG", product_playbook=GUARANTEE)
        s.add(case)
        s.commit()
        add_document(
            s,
            case,
            "BANK_GUARANTEE",
            {"required_demand_conditions": "Signed demand plus statement of breach"},
        )
        demand = add_document(s, case, "GUARANTEE_DEMAND", {"demand_reference": "DM-001"})
        first = run_examination(s, Settings(_env_file=None), case.case_id)
        assert not first.findings
        add_document(
            s,
            case,
            "GUARANTEE_DEMAND",
            {"notice": "Required breach statement intentionally absent"},
            document=demand,
        )
        second = run_examination(s, Settings(_env_file=None), case.case_id)
        assert [f.finding_type for f in second.findings] == ["REQUIRED_BREACH_STATEMENT_MISSING"]
        assert second.findings[0].observed_json["field_name"] == "notice"
