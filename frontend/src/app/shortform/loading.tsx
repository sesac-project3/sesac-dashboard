// 숏폼 탭을 처음 누르면 page.tsx의 서버 컴포넌트가 백엔드 fetch(+S3 URL 조회)를 끝낼
// 때까지 아무것도 안 보이던 문제 — loading.tsx가 없으면 Next.js가 그 fetch가 끝날 때까지
// 화면을 그대로 안 바꾼다. 이 파일이 있으면 네비게이션 즉시 이 스켈레톤부터 보여주고,
// 데이터가 준비되는 대로 실제 피드로 교체한다(App Router의 자동 Suspense 경계).
export default function ShortformLoading() {
  return (
    <div className="flex h-full w-full items-center justify-center bg-black">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-white/20 border-t-white/70" />
    </div>
  );
}
