import { Footer } from "nhsuk-react-components";

export function SiteFooter() {
  return (
    <Footer>
      <Footer.List>
        <Footer.ListItem href="/patients">Patient search</Footer.ListItem>
        <Footer.ListItem href="/quality">Quality dashboard</Footer.ListItem>
        <Footer.ListItem href="/admin">Audit log</Footer.ListItem>
      </Footer.List>
      <Footer.Copyright>© Clerkstone — portfolio prototype</Footer.Copyright>
    </Footer>
  );
}
