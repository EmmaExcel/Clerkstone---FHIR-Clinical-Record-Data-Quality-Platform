import { Heading } from "nhsuk-react-components";

export function PageHeader({ title, caption }: { title: string; caption?: string }) {
  return (
    <div>
      {caption ? <span className="nhsuk-caption-xl">{caption}</span> : null}
      <Heading headingLevel="h1" size="xl">
        {title}
      </Heading>
    </div>
  );
}
