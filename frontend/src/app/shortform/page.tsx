import { API_BASE_URL } from "@/shared/config/env";
import type { Shortform } from "@/entities/shortform/types";
import ShortformCard from "@/widgets/shortform-feed/ShortformCard";

async function fetchShortforms(): Promise<Shortform[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/shortforms`, { cache: "no-store" });
    if (!res.ok) return [];
    const body = await res.json(); // ApiResponse 봉투
    return body.data ?? [];
  } catch {
    return [];
  }
}

export default async function ShortformPage() {
  const shortforms = await fetchShortforms();

  if (shortforms.length === 0) {
    return (
      <div className="p-4">
        <h1 className="mb-4 text-lg font-semibold">숏폼</h1>
        <p className="text-sm text-black/50">아직 준비된 영상이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="flex snap-y snap-mandatory flex-col gap-4 overflow-y-auto p-4">
      {shortforms.map((sf) => (
        <div key={sf.id} className="snap-start">
          <ShortformCard shortform={sf} />
        </div>
      ))}
    </div>
  );
}
