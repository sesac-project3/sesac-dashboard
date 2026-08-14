// 로그인 후 홈 대시보드 최초 데이터 로딩 중에만 보여주는 풀스크린 로딩 화면
// (MarketDashboard의 showLoadingScreen 상태). 이후 5초 주기 자동 갱신/새로고침 때는
// 이 화면이 다시 뜨지 않는다.
export default function HomeLoadingScreen({ percent }: { percent: number }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-between px-6 py-12">
      <div />
      <div className="flex flex-col items-center gap-8">
        {/* eslint-disable-next-line @next/next/no-img-element -- 로고 1개뿐, next/image 불필요 */}
        <img
          src="/img/logo/zstock_logo.png"
          alt="Z-STOCK"
          className="w-40 max-w-[60vw] select-none drop-shadow-[0_10px_24px_rgba(84,43,233,0.25)]"
        />
        <div className="flex flex-col items-center gap-2">
          <div className="h-1 w-48 overflow-hidden rounded-full bg-surface">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className="text-[11px] font-medium text-caption">{percent}%</span>
        </div>
      </div>
      <p className="text-[11px] font-medium tracking-wide text-caption uppercase">
        Powered by AI Analysis
      </p>
    </div>
  );
}
