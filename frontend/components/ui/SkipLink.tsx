import { SkipLink as NhsSkipLink } from "nhsuk-react-components";

/**
 * NHS.UK skip link. The default `#maincontent` target matches the `id` on the
 * `<main>` element in the root layout, so keyboard and screen-reader users can
 * bypass the header/navigation on every page.
 */
export function SkipLink() {
  return <NhsSkipLink href="#maincontent">Skip to main content</NhsSkipLink>;
}
