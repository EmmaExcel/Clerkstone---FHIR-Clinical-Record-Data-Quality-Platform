"""Physiological-plausibility rules (category: physiological).

Ranges are cited in each rule description. A value outside the *impossible*
range is an error (usually a decimal-point or unit error); a value outside the
*plausible* range but inside the impossible range is a warning.
"""

from __future__ import annotations

from app.domain.quality.rules.base import (
    SEVERITY_ERROR,
    Rule,
    RuleContext,
)


def _display_text(resource: dict) -> str:
    code = resource.get("code") or {}
    coding = (code.get("coding") or [{}])[0] or {}
    return (coding.get("display") or code.get("text") or "").lower()


class _VitalRule(Rule):
    """Shared implementation for a physiological range check."""

    codes: frozenset[str] = frozenset()
    display_tokens: tuple[str, ...] = ()
    impossible: tuple[float, float] = (float("-inf"), float("inf"))
    plausible: tuple[float, float] = (float("-inf"), float("inf"))
    unit: str = ""
    reference: str = ""
    sentinel_values: tuple[float, ...] = ()

    def _matches(self, resource: dict) -> bool:
        for coding in (resource.get("code") or {}).get("coding") or []:
            if coding.get("code") in self.codes:
                return True
        text = _display_text(resource)
        return any(tok in text for tok in self.display_tokens)

    def evaluate(self, ctx: RuleContext) -> list:
        if not self._matches(ctx.resource):
            return []
        value = ((ctx.resource.get("valueQuantity") or {}).get("value"))
        if value is None:
            return []
        try:
            value = float(value)
        except (TypeError, ValueError):
            return []

        ctx_detail = {
            "value": value,
            "unit": (ctx.resource.get("valueQuantity") or {}).get("unit") or self.unit,
            "reference": self.reference,
        }

        if self.sentinel_values and value in self.sentinel_values:
            return [
                self._finding(
                    ctx,
                    f"{self.title}: value {value} {self.unit} is a sentinel value "
                    f"(commonly used for 'not recorded').",
                    context=ctx_detail,
                )
            ]

        lo_i, hi_i = self.impossible
        lo_p, hi_p = self.plausible
        if value < lo_i or value > hi_i:
            return [
                self._finding(
                    ctx,
                    f"{self.title}: value {value} {self.unit} is outside the impossible "
                    f"range {lo_i}–{hi_i} (reference: {self.reference}).",
                    context=ctx_detail,
                )
            ]
        if value < lo_p or value > hi_p:
            return [
                self._finding(
                    ctx,
                    f"{self.title}: value {value} {self.unit} is outside the plausible "
                    f"range {lo_p}–{hi_p} (reference: {self.reference}).",
                    context=ctx_detail,
                )
            ]
        return []


class SystolicBp(_VitalRule):
    id = "PHYS-001"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Systolic blood pressure implausible"
    description = "Systolic BP outside 30–300 mmHg (impossible) or 70–200 mmHg (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit; a decimal-point shift (e.g. 1420) is the usual cause."
    codes = frozenset({"271649006", "8480-6"})
    display_tokens = ("systolic blood pressure", "systolic bp")
    impossible = (30, 300)
    plausible = (70, 200)
    unit = "mm[Hg]"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class DiastolicBp(_VitalRule):
    id = "PHYS-002"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Diastolic blood pressure implausible"
    description = "Diastolic BP outside 20–200 mmHg (impossible) or 40–120 mmHg (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"271650006", "8462-4"})
    display_tokens = ("diastolic blood pressure", "diastolic bp")
    impossible = (20, 200)
    plausible = (40, 120)
    unit = "mm[Hg]"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class HeartRate(_VitalRule):
    id = "PHYS-003"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Heart rate implausible"
    description = "Heart rate outside 15–300 bpm (impossible) or 40–180 bpm (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"364075005", "8867-4"})
    display_tokens = ("heart rate", "pulse rate")
    impossible = (15, 300)
    plausible = (40, 180)
    unit = "beats/min"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class SpO2(_VitalRule):
    id = "PHYS-004"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Oxygen saturation implausible"
    description = "SpO2 outside 40–100 % (impossible) or 80–100 % (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = (
        "0 and 100 are commonly sentinel values for 'not recorded' — replace with the true value or omit."
    )
    codes = frozenset({"431314004", "59408-5", "2708-6"})
    display_tokens = ("oxygen saturation", "spo2", "o2 sat")
    impossible = (40, 100)
    plausible = (80, 100)
    unit = "%"
    reference = "RCP/NICE adult ranges; see rule definition"
    sentinel_values = (0.0, 100.0)
    applies_to = frozenset({"Observation"})


class Temperature(_VitalRule):
    id = "PHYS-005"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Body temperature implausible"
    description = "Temperature outside 30–45 °C (impossible) or 35–42 °C (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit (°C vs °F is a common confusion)."
    codes = frozenset({"386725007", "8310-5"})
    display_tokens = ("body temperature", "temperature")
    impossible = (30, 45)
    plausible = (35, 42)
    unit = "degC"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class Weight(_VitalRule):
    id = "PHYS-006"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Body weight implausible"
    description = "Weight outside 0.5–400 kg (impossible) or 2–300 kg (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit (kg vs lb is a common confusion)."
    codes = frozenset({"27113001", "29463-7"})
    display_tokens = ("body weight", "weight")
    impossible = (0.5, 400)
    plausible = (2, 300)
    unit = "kg"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class Height(_VitalRule):
    id = "PHYS-007"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Body height implausible"
    description = "Height outside 20–250 cm (impossible) or 50–230 cm (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit (cm vs m is a common confusion)."
    codes = frozenset({"50373000", "8302-2"})
    display_tokens = ("body height", "height")
    impossible = (20, 250)
    plausible = (50, 230)
    unit = "cm"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class RespiratoryRate(_VitalRule):
    id = "PHYS-008"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Respiratory rate implausible"
    description = "Respiratory rate outside 4–80 /min (impossible) or 8–40 /min (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"86290005", "9279-1"})
    display_tokens = ("respiratory rate", "respiration rate")
    impossible = (4, 80)
    plausible = (8, 40)
    unit = "/min"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class Bmi(_VitalRule):
    id = "PHYS-009"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Body mass index implausible"
    description = "BMI outside 5–100 kg/m2 (impossible) or 12–60 kg/m2 (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"60621009", "39156-5"})
    display_tokens = ("body mass index", "bmi")
    impossible = (5, 100)
    plausible = (12, 60)
    unit = "kg/m2"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class BloodGlucose(_VitalRule):
    id = "PHYS-010"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Blood glucose implausible"
    description = "Blood glucose outside 0.1–100 mmol/L (impossible) or 2–40 mmol/L (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"434912009", "2345-7"})
    display_tokens = ("blood glucose", "glucose")
    impossible = (0.1, 100)
    plausible = (2, 40)
    unit = "mmol/L"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class SerumPotassium(_VitalRule):
    id = "PHYS-011"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Serum potassium implausible"
    description = "Serum potassium outside 1–15 mmol/L (impossible) or 2.5–7 mmol/L (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"59573005", "6298-4"})
    display_tokens = ("potassium",)
    impossible = (1, 15)
    plausible = (2.5, 7)
    unit = "mmol/L"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class SerumCreatinine(_VitalRule):
    id = "PHYS-012"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "Serum creatinine implausible"
    description = "Serum creatinine outside 1–5000 umol/L (impossible) or 20–1000 umol/L (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"70901006", "2160-0"})
    display_tokens = ("creatinine",)
    impossible = (1, 5000)
    plausible = (20, 1000)
    unit = "umol/L"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})


class Inr(_VitalRule):
    id = "PHYS-013"
    category = "physiological"
    severity = SEVERITY_ERROR
    title = "INR implausible"
    description = "INR outside 0.1–100 (impossible) or 0.8–10 (plausible)."
    fhirpath = "Observation.valueQuantity.value"
    suggested_action = "Confirm the value and unit."
    codes = frozenset({"165581004", "34714-6"})
    display_tokens = ("inr", "international normalized ratio")
    impossible = (0.1, 100)
    plausible = (0.8, 10)
    unit = "1"
    reference = "RCP/NICE adult ranges; see rule definition"
    applies_to = frozenset({"Observation"})
