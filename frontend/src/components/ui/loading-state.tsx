type LoadingStateProps = {
  label: string;
};

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div aria-live="polite" className="loading-state" role="status">
      <span className="loading-state__dot" />
      <span>{label}</span>
    </div>
  );
}
