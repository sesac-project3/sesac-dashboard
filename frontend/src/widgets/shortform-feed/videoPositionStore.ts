// 다른 탭(홈/내정보)으로 갔다가 숏폼으로 돌아오면 Next.js가 이 페이지의 컴포넌트를
// 통째로 언마운트했다 다시 마운트한다 — React state/ref가 다 날아가서 영상이 항상
// 처음부터 재생됐다. 컴포넌트 생명주기 밖(모듈 스코프)에 마지막 재생 위치를 들고
// 있다가, 10초 안에 돌아오면 그 지점부터 이어서 보여준다. 세션 전역에 하나면 되고
// 새로고침/탭 닫기까지 버틸 필요는 없어서 sessionStorage/localStorage 없이 메모리로 충분.
const RESUME_WINDOW_MS = 10_000;

const lastPositions = new Map<number, { time: number; savedAt: number }>();

export function saveVideoPosition(shortformId: number, time: number) {
  lastPositions.set(shortformId, { time, savedAt: Date.now() });
}

export function getResumePosition(shortformId: number): number | null {
  const entry = lastPositions.get(shortformId);
  if (!entry) return null;
  if (Date.now() - entry.savedAt > RESUME_WINDOW_MS) return null;
  return entry.time;
}
