import { Container } from "nhsuk-react-components";

export function SyntheticDataBanner() {
  return (
    <div className="clerkstone-data-banner" role="note" aria-label="Synthetic data notice">
      <Container>
        <div className="clerkstone-data-banner__inner">
          
          <div>
            <p className="clerkstone-data-banner__text">Synthetic data , not for clinical use</p>
            <p className="clerkstone-data-banner__text--sub">
              All patient records in this system are synthetically generated. This is a portfolio
              prototype and must not be used for patient care or clinical decisions.
            </p>
          </div>
        </div>
      </Container>
    </div>
  );
}
