"""SQLAlchemy 2.0 models — the relational/JSONB hybrid schema.

The FHIR resource (JSONB in ``fhir_resource``) is the source of truth; every
other table is a *derived projection* that must be rebuildable from it. See
docs/architecture.md and docs/DECISIONS.md (ADR-003).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class FhirResource(Base):
    __tablename__ = "fhir_resource"
    __table_args__ = (UniqueConstraint("resource_type", "logical_id", "version_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    logical_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(Text, nullable=False, default="1")
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_bundle: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ingestion_bundle.id"), nullable=True
    )
    security_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class IngestionBundle(Base):
    __tablename__ = "ingestion_bundle"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    uploaded_by: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_count: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)  # accepted | partial | rejected
    operation_outcome: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class Patient(Base):
    __tablename__ = "patient"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fhir_resource.id", ondelete="CASCADE"), primary_key=True
    )
    logical_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    nhs_number: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    nhs_number_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    given_names: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(Text, nullable=True)
    deceased: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    postcode: Mapped[str | None] = mapped_column(Text, nullable=True)  # outward code only

    resource: Mapped["FhirResource"] = relationship(lazy="joined")


class Encounter(Base):
    __tablename__ = "encounter"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fhir_resource.id", ondelete="CASCADE"), primary_key=True
    )
    logical_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient.resource_id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    class_: Mapped[str | None] = mapped_column("class", Text, nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admission_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    discharge_disposition: Mapped[str | None] = mapped_column(Text, nullable=True)


class Observation(Base):
    __tablename__ = "observation"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fhir_resource.id", ondelete="CASCADE"), primary_key=True
    )
    logical_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient.resource_id", ondelete="CASCADE"), nullable=False, index=True
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("encounter.resource_id", ondelete="SET NULL"), nullable=True
    )
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    code_system: Mapped[str] = mapped_column(Text, nullable=False)
    code_value: Mapped[str] = mapped_column(Text, nullable=False)
    code_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_quantity: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    value_unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)


class Condition(Base):
    __tablename__ = "condition"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fhir_resource.id", ondelete="CASCADE"), primary_key=True
    )
    logical_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient.resource_id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_system: Mapped[str] = mapped_column(Text, nullable=False)
    code_value: Mapped[str] = mapped_column(Text, nullable=False)
    code_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    onset_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    abatement_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)


class MedicationRequest(Base):
    __tablename__ = "medication_request"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fhir_resource.id", ondelete="CASCADE"), primary_key=True
    )
    logical_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient.resource_id", ondelete="CASCADE"), nullable=False, index=True
    )
    dm_d_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    dm_d_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    authored_on: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    dosage_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class DqRuleset(Base):
    __tablename__ = "dq_ruleset"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    version: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    rule_count: Mapped[int] = mapped_column(nullable=False)


class DqRule(Base):
    __tablename__ = "dq_rule"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # stable: 'TEMP-003'
    ruleset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("dq_ruleset.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)  # error | warning | info
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    fhirpath: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DqRun(Base):
    __tablename__ = "dq_run"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    ruleset_version: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    counts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class DqFinding(Base):
    __tablename__ = "dq_finding"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("dq_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(Text, ForeignKey("dq_rule.id"), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("fhir_resource.id"), nullable=True
    )
    resource_logical_id: Mapped[str] = mapped_column(Text, nullable=False)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("patient.resource_id"), nullable=True
    )
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    review_status: Mapped[str] = mapped_column(Text, nullable=False, default="open")


class ReviewTask(Base):
    __tablename__ = "review_task"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("dq_finding.id"), nullable=False, index=True
    )
    assigned_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class AuditEvent(Base):
    """Append-only, hash-chained audit log. No UPDATE/DELETE by application role."""

    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    actor_role: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)  # success | denied | error
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    prev_hash: Mapped[str] = mapped_column(Text, nullable=False)
    event_hash: Mapped[str] = mapped_column(Text, nullable=False)


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    subject: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # reader | analyst | admin
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
