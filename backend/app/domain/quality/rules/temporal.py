from __future__ import annotations

from datetime import UTC, datetime

from app.domain.quality.rules.base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    Rule,
    RuleContext,
)
from app.domain.quality.rules.util import parse_date, parse_datetime

_MAX_REASONABLE_AGE_YEARS = 130


def _now() -> datetime:
    return datetime.now(UTC)


class BirthDateInFuture(Rule):
    id = "TEMP-001"
    category = "temporal"
    severity = SEVERITY_ERROR
    title = "Birth date in the future"
    description = "Patient.birthDate is after the current date."
    fhirpath = "Patient.birthDate"
    suggested_action = "Correct the birth date; future dates usually indicate a date-format or timezone error."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        bd = parse_date(ctx.resource.get("birthDate"))
        if bd is not None and bd > _now().date():
            return [
                self._finding(
                    ctx,
                    f"Patient.birthDate {bd.isoformat()} is after the current date.",
                    context={"birth_date": bd.isoformat()},
                )
            ]
        return []


class BirthDateTooOld(Rule):
    id = "TEMP-002"
    category = "temporal"
    severity = SEVERITY_WARNING
    title = "Birth date implausibly old"
    description = f"Patient.birthDate is more than {_MAX_REASONABLE_AGE_YEARS} years in the past."
    fhirpath = "Patient.birthDate"
    suggested_action = "Confirm the birth date; very old dates often indicate a default or placeholder value."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        bd = parse_date(ctx.resource.get("birthDate"))
        if bd is None:
            return []
        age_days = (_now().date() - bd).days
        if age_days > _MAX_REASONABLE_AGE_YEARS * 365.25:
            return [
                self._finding(
                    ctx,
                    f"Patient.birthDate {bd.isoformat()} is over {_MAX_REASONABLE_AGE_YEARS} years in the past.",
                    context={"birth_date": bd.isoformat()},
                )
            ]
        return []


class EncounterEndBeforeStart(Rule):
    id = "TEMP-003"
    category = "temporal"
    severity = SEVERITY_ERROR
    title = "Encounter period ends before it starts"
    description = "Encounter.period.end precedes Encounter.period.start."
    fhirpath = "Encounter.period.end"
    suggested_action = (
        "Confirm source-system timezone handling; records migrated from a system using local "
        "time commonly exhibit this defect."
    )
    applies_to = frozenset({"Encounter"})

    def evaluate(self, ctx: RuleContext) -> list:
        period = ctx.resource.get("period") or {}
        start = parse_datetime(period.get("start"))
        end = parse_datetime(period.get("end"))
        if start and end and end < start:
            delta_hours = (end - start).total_seconds() / 3600
            return [
                self._finding(
                    ctx,
                    f"Encounter.period.end ({end.isoformat()}) precedes start ({start.isoformat()}).",
                    context={
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "delta_hours": round(delta_hours, 2),
                    },
                )
            ]
        return []


class DeathBeforeBirth(Rule):
    id = "TEMP-004"
    category = "temporal"
    severity = SEVERITY_ERROR
    title = "Death date before birth date"
    description = "Patient.deceasedDateTime precedes Patient.birthDate."
    fhirpath = "Patient.deceasedDateTime"
    suggested_action = "Correct the death or birth date."
    applies_to = frozenset({"Patient"})

    def evaluate(self, ctx: RuleContext) -> list:
        bd = parse_date(ctx.resource.get("birthDate"))
        dd = parse_datetime(ctx.resource.get("deceasedDateTime"))
        if bd and dd and dd.date() < bd:
            return [
                self._finding(
                    ctx,
                    f"deceasedDateTime {dd.isoformat()} precedes birthDate {bd.isoformat()}.",
                    context={"birth_date": bd.isoformat(), "death": dd.isoformat()},
                )
            ]
        return []


class ObservationBeforeBirth(Rule):
    id = "TEMP-005"
    category = "temporal"
    severity = SEVERITY_WARNING
    title = "Observation effective before patient birth"
    description = "Observation effective time precedes the subject Patient.birthDate."
    fhirpath = "Observation.effective[x]"
    suggested_action = "Confirm the observation timestamp and the linked patient."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        patient = ctx.patient
        if not patient:
            return []
        bd = parse_date(patient.get("birthDate"))
        eff = parse_datetime(ctx.resource.get("effectiveDateTime"))
        if eff is None:
            eff = parse_datetime((ctx.resource.get("effectivePeriod") or {}).get("start"))
        if bd and eff and eff.date() < bd:
            return [
                self._finding(
                    ctx,
                    f"Observation effective {eff.isoformat()} precedes birth date {bd.isoformat()}.",
                    context={"birth_date": bd.isoformat(), "effective": eff.isoformat()},
                )
            ]
        return []


class ObservationAfterDeath(Rule):
    id = "TEMP-006"
    category = "temporal"
    severity = SEVERITY_ERROR
    title = "Observation after patient death"
    description = "Observation recorded after the subject Patient.deceasedDateTime."
    fhirpath = "Observation.effective[x]"
    suggested_action = (
        "Resolve the conflicting timestamps; later observations on a deceased "
        "patient usually indicate a wrong subject link."
    )
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        patient = ctx.patient
        if not patient:
            return []
        dd = parse_datetime(patient.get("deceasedDateTime"))
        eff = parse_datetime(ctx.resource.get("effectiveDateTime"))
        if eff is None:
            eff = parse_datetime((ctx.resource.get("effectivePeriod") or {}).get("start"))
        if dd and eff and eff > dd:
            return [
                self._finding(
                    ctx,
                    f"Observation effective {eff.isoformat()} is after deceasedDateTime {dd.isoformat()}.",
                    context={"death": dd.isoformat(), "effective": eff.isoformat()},
                )
            ]
        return []


class ConditionOnsetAfterAbatement(Rule):
    id = "TEMP-007"
    category = "temporal"
    severity = SEVERITY_ERROR
    title = "Condition onset after abatement"
    description = "Condition onset date is after its abatement date."
    fhirpath = "Condition.abatement[x]"
    suggested_action = "Correct the condition onset/abatement dates."
    applies_to = frozenset({"Condition"})

    def evaluate(self, ctx: RuleContext) -> list:
        onset = parse_date(ctx.resource.get("onsetDateTime"))
        abatement = parse_date(ctx.resource.get("abatementDateTime"))
        if onset and abatement and abatement < onset:
            return [
                self._finding(
                    ctx,
                    f"Condition.abatement {abatement.isoformat()} precedes onset {onset.isoformat()}.",
                    context={"onset": onset.isoformat(), "abatement": abatement.isoformat()},
                )
            ]
        return []


class ObservationEffectiveInFuture(Rule):
    id = "TEMP-008"
    category = "temporal"
    severity = SEVERITY_ERROR
    title = "Observation effective in the future"
    description = "Observation effective time is after the current date/time."
    fhirpath = "Observation.effective[x]"
    suggested_action = "Correct the timestamp; future-dated observations usually indicate a clock or timezone error."
    applies_to = frozenset({"Observation"})

    def evaluate(self, ctx: RuleContext) -> list:
        eff = parse_datetime(ctx.resource.get("effectiveDateTime"))
        if eff is None:
            eff = parse_datetime((ctx.resource.get("effectivePeriod") or {}).get("start"))
        if eff and eff > _now():
            return [
                self._finding(
                    ctx,
                    f"Observation effective {eff.isoformat()} is in the future.",
                    context={"effective": eff.isoformat()},
                )
            ]
        return []


class ConditionOnsetInFuture(Rule):
    id = "TEMP-009"
    category = "temporal"
    severity = SEVERITY_WARNING
    title = "Condition onset in the future"
    description = "Condition onset is after the current date."
    fhirpath = "Condition.onset[x]"
    suggested_action = "Correct the onset date."
    applies_to = frozenset({"Condition"})

    def evaluate(self, ctx: RuleContext) -> list:
        onset = parse_datetime(ctx.resource.get("onsetDateTime"))
        if onset and onset > _now():
            return [
                self._finding(
                    ctx,
                    f"Condition onset {onset.isoformat()} is in the future.",
                    context={"onset": onset.isoformat()},
                )
            ]
        return []
