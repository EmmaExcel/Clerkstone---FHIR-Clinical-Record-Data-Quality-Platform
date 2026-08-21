import { describe, expect, it } from "vitest";
import { resolveFhirPath } from "@/components/resource-viewer/fhirpath";

const encounter = {
  resourceType: "Encounter",
  period: { start: "2026-09-01T09:02:00Z", end: "2026-08-30T10:00:00Z" },
};

const patient = {
  resourceType: "Patient",
  identifier: [
    { system: "https://fhir.nhs.uk/Id/nhs-number", value: "9900000001" },
    { system: "urn:oid:1.2.840.114350.1.13", value: "MRN-123" },
  ],
  name: [{ family: "Okonkwo", given: ["Amara"] }],
};

describe("resolveFhirPath", () => {
  it("resolves a nested property to a JSON pointer", () => {
    expect(resolveFhirPath(encounter, "Encounter.period.end")).toEqual(["/period/end"]);
  });

  it("resolves an indexed array element", () => {
    expect(resolveFhirPath(patient, "Patient.identifier[0].value")).toEqual(["/identifier/0/value"]);
  });

  it("resolves a whole array property", () => {
    expect(resolveFhirPath(patient, "Patient.identifier")).toEqual(["/identifier"]);
  });

  it("returns an empty array when the path does not exist", () => {
    expect(resolveFhirPath(encounter, "Encounter.class")).toEqual([]);
  });

  it("returns an empty array for unsupported/empty expressions", () => {
    expect(resolveFhirPath(encounter, "")).toEqual([]);
    expect(resolveFhirPath(null, "Encounter.period")).toEqual([]);
  });
});
