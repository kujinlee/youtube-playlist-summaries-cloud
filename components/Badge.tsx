interface BadgeProps {
  label: string;
  colorClass: string;
}

export default function Badge({ label, colorClass }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}
