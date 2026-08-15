import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";
import { SkipLink } from "@/components/ui/SkipLink";
import { SiteHeader } from "@/components/ui/SiteHeader";
import { SiteFooter } from "@/components/ui/SiteFooter";
import { SyntheticDataBanner } from "@/components/ui/SyntheticDataBanner";
import "nhsuk-frontend/dist/nhsuk/nhsuk-frontend-10.6.1.min.css";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Clerkstone — FHIR Clinical Record & Data Quality Platform",
    template: "%s | Clerkstone",
  },
  description:
    "Synthetic FHIR R4 clinical record and data-quality platform. Portfolio prototype — not for clinical use.",
};

export const viewport: Viewport = {
  themeColor: "#005eb8",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "document.body.className += ' js-enabled' + ('noModule' in HTMLScriptElement.prototype ? ' nhsuk-frontend-supported' : '');",
          }}
        />
        <Providers>
          <SkipLink />
          <SiteHeader />
          <SyntheticDataBanner />
          <div className="nhsuk-width-container">
            <main className="nhsuk-main-wrapper" id="maincontent">
              <div className="nhsuk-width-container">{children}</div>
            </main>
          </div>
          <SiteFooter />
        </Providers>
      </body>
    </html>
  );
}
