export default function Loading() {
  return (
    <div className="flex flex-col gap-4 p-5" aria-label="종목 상세 로딩 중">
      <div className="h-40 animate-pulse rounded-lg bg-surface" />
      <div className="h-72 animate-pulse rounded-lg bg-surface" />
    </div>
  );
}
