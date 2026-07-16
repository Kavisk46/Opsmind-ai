interface AuthDividerProps {
  label?: string;
}

export function AuthDivider({ label = "or continue with" }: AuthDividerProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-px flex-1 bg-border" aria-hidden="true" />
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="h-px flex-1 bg-border" aria-hidden="true" />
    </div>
  );
}
