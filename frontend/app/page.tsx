import { Card, Container } from "nhsuk-react-components";
import { BackendHealthStatus } from "@/components/ui/BackendHealthStatus";
import { PageHeader } from "@/components/ui/PageHeader";

export default function HomePage() {
  return (
    <Container>
      <PageHeader
        title="Clerkstone"
        caption="FHIR R4 clinical record & data-quality platform"
      />

      <p className="nhsuk-lede-text">
        A portfolio prototype that ingests synthetic FHIR R4 patient records, validates them, and
        surfaces the data-quality defects that break real EPR migrations.
      </p>

      <BackendHealthStatus />

      <Card.Group>
        <Card.GroupItem width="one-third">
          <Card clickable>
            <Card.Heading headingLevel="h2">Patient search</Card.Heading>
            <Card.Description>
              Search patients by name, date of birth or gender, and open a clinical timeline.
            </Card.Description>
            <Card.Link href="/patients">Find a patient</Card.Link>
          </Card>
        </Card.GroupItem>
        <Card.GroupItem width="one-third">
          <Card clickable>
            <Card.Heading headingLevel="h2">Quality dashboard</Card.Heading>
            <Card.Description>
              Review quality runs, drill from a finding to the exact FHIR element that caused it.
            </Card.Description>
            <Card.Link href="/quality">Open the quality dashboard</Card.Link>
          </Card>
        </Card.GroupItem>
        <Card.GroupItem width="one-third">
          <Card clickable>
            <Card.Heading headingLevel="h2">Audit log</Card.Heading>
            <Card.Description>
              Inspect the append-only, hash-chained audit trail (admin).
            </Card.Description>
            <Card.Link href="/admin">View the audit log</Card.Link>
          </Card>
        </Card.GroupItem>
      </Card.Group>
    </Container>
  );
}
