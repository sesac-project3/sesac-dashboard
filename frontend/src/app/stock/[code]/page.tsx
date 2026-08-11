import { API_BASE_URL } from "@/shared/config/env";
import type { StockReport } from "@/entities/report/types";

async function fetchReport(code: string): Promise<StockReport | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/reports/${code}`, { cache: "no-store" });
    if (!res.ok) return null;
    const body = await res.json(); // ApiResponse 봉투
    return body.data;
  } catch {
    return null;
  }
}

export default async function StockReportPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const report = await fetchReport(code);

  return (
    <div className="flex flex-col gap-4 p-4">
      <h1 className="text-lg font-semibold">{code} 리포트</h1>

      {/* F-03-1: 근거 없으면 블록 자체를 숨긴다 */}
      {report?.judgement && report.judgementReasons && (
        <section className="rounded-lg border border-black/10 p-3">
          <p className="font-semibold">AI 판단: {report.judgement}</p>
          <ul className="mt-2 list-disc pl-4 text-sm">
            {report.judgementReasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        </section>
      )}

      {!report && <p className="text-sm text-black/50">리포트를 준비 중입니다.</p>}

      <p className="text-xs text-black/40">
        본 정보는 투자 참고 자료이며 투자 권유가 아닙니다. 투자 판단과 그 결과에 대한 책임은
        이용자 본인에게 있습니다.
      </p>
    </div>
  );
}
