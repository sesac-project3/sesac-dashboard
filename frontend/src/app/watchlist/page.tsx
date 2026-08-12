import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";

// F-04 관심종목. 백엔드 API가 아직 없어(watchlists 테이블만 존재) 우선 빈 상태만 노출한다
// — BottomTabBar 4탭 구성을 먼저 완성하기 위한 자리(placeholder), 목록/추가 로직은 별도 작업.
export default function WatchlistPage() {
  return (
    <PageContainer>
      <h1 className="my-4 text-[18px] font-semibold text-heading">관심종목</h1>
      <Card className="text-center text-[14px] text-caption">
        아직 담은 종목이 없습니다.
      </Card>
    </PageContainer>
  );
}
