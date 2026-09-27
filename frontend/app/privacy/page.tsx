import { Container } from "nhsuk-react-components";
import { PageHeader } from "@/components/ui/PageHeader";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy",
};

export default function PrivacyPage() {
  return (
    <Container>
      <PageHeader title="Privacy Policy" />
      <div className="nhsuk-reading-width">
        <p>
          This is a portfolio prototype built for demonstration purposes. It does not collect,
          process, or store any real patient or personal data.
        </p>
        <h2>Data Collection</h2>
        <p>
          The system uses purely synthetic, computer-generated data to demonstrate data quality
          mechanisms. No tracking cookies or analytics are deployed on this platform.
        </p>
      </div>
    </Container>
  );
}
