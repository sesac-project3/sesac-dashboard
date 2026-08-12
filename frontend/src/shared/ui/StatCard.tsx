// DESIGN_SPEC.md §12.3 Stat Card — label caption gray, value bold, 동일 높이.
export default function StatCard({
  label,
  value,
  valueClassName = "",
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex h-full flex-col justify-between gap-2 rounded-lg border border-border-soft bg-white p-4 shadow-card">
      <p className="text-[13px] text-caption">{label}</p>
      <p className={`text-[22px] leading-tight font-bold text-heading ${valueClassName}`}>
        {value}
      </p>
    </div>
  );
}
