import { Container } from "nhsuk-react-components";

export function SyntheticDataBanner() {
  return (
    <div className="clerkstone-data-banner" role="note" aria-label="Synthetic data notice">
      <Container>
        <div className="clerkstone-data-banner__inner">
          <span className="clerkstone-data-banner__icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" focusable="false">
              <path d="M12 2 1 21h22L12 2zm1 14h-2v2h2v-2zm0-7h-2v5h2V9z" />
            </svg>
          </span>
          <div>
            <p className="clerkstone-data-banner__text">Synthetic data — not for clinical use</p>
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
