type PageHeadingProps = {
  eyebrow?: string;
  title: string;
  subtitle: string;
};

export function PageHeading({ eyebrow, title, subtitle }: PageHeadingProps) {
  return (
    <header className="page-heading">
      {eyebrow ? <p className="page-heading__eyebrow">{eyebrow}</p> : null}
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
    </header>
  );
}
