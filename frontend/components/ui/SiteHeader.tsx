"use client";

import { Header } from "nhsuk-react-components";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/patients", label: "Patients" },
  { href: "/quality", label: "Quality" },
  { href: "/admin", label: "Admin" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <Header logo={{ href: "/", src: "/clerkstone-logo.svg", alt: "Clerkstone" }}>
      <Header.Navigation aria-label="Primary navigation">
        {NAV_ITEMS.map((item) => (
          <Header.NavigationItem key={item.href} href={item.href} current={isActive(pathname, item.href)}>
            {item.label}
          </Header.NavigationItem>
        ))}
      </Header.Navigation>
    </Header>
  );
}
