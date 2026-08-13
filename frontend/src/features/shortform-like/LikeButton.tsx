"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toggleShortformLike } from "@/shared/api/shortforms";
import { getAccessToken } from "@/shared/api/base";

// 인스타그램 스타일: 평소엔 흰색 outline 하트, 좋아요 누르면 빨간 채움 하트 + 살짝 튀는(pop)
// 스케일 애니메이션. DESIGN_SPEC.md 410행 "active favorite: red 계열" 규칙 적용.
function HeartIcon({ filled, popping }: { filled: boolean; popping: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={`h-7 w-7 drop-shadow transition-transform duration-200 ease-out ${
        popping ? "scale-125" : "scale-100"
      } ${filled ? "text-red-500" : "text-white"}`}
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={filled ? 0 : 1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
    </svg>
  );
}

export default function LikeButton({
  shortformId,
  initialLiked = false,
  initialCount,
}: {
  shortformId: number;
  initialLiked?: boolean;
  initialCount: number;
}) {
  const router = useRouter();
  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const [popping, setPopping] = useState(false);
  // "가장 최근에 보낸 요청" 번호 — 응답이 왔을 때 그 사이 더 최신 클릭이 있었으면
  // (=이 번호가 바뀌어 있으면) 낡은 응답은 버린다. requestChain은 실제 네트워크 호출을
  // 한 번에 하나씩만 순서대로 내보내기 위한 체인. 아래 onClick 주석 참고.
  const latestRequestId = useRef(0);
  const requestChain = useRef<Promise<unknown>>(Promise.resolve());
  const hasInteracted = useRef(false);

  // ShortformFeed는 /shortforms를 서버 컴포넌트가 캐시 걸어 먼저 렌더한 뒤(그 시점엔
  // liked가 항상 false), 브라우저에서 로그인 토큰으로 내 좋아요 목록을 따로 가져와
  // 뒤늦게 shortform.liked를 갱신한다 — 이 컴포넌트는 이미 initialLiked=false로 마운트가
  // 끝난 뒤라 useState(initialLiked)의 초기값은 다시 안 쓰인다. 그래서 prop이 나중에
  // 바뀌면 이 effect로 동기화해준다. 단, 그 사이 사용자가 이미 클릭했다면(hasInteracted)
  // 그 클릭이 우선이니 덮어쓰지 않는다.
  useEffect(() => {
    if (!hasInteracted.current) setLiked(initialLiked);
  }, [initialLiked]);

  // 낙관적 업데이트: 서버 응답 기다리지 않고 하트/카운트를 바로 바꾸고, 실제 토글은
  // 백그라운드에서 처리한다. 실패했을 때만 원래 값으로 되돌린다(관심종목 하트와 동일 패턴).
  //
  // 1초 안에 여러 번 클릭할 때 겪었던 두 가지 버그와 수정 이유:
  // 1) "이미 요청 중이면 새 요청은 안 보냄" 방식이었을 때 — 맨 처음 요청의 응답이 나중에
  //    도착하면서 그 사이 여러 번 더 눌러 만든 최신 화면을 덮어써서 다른 값으로 보였다.
  // 2) 클릭마다 매번 서버로 보내되 응답만 "최신 것만 반영"하도록 고쳤더니, 이번엔 같은
  //    좋아요에 대한 토글 요청 여러 개가 서버에 동시에 도착해 DB에서 경합해 요청 하나가
  //    통째로 실패하는 문제가 실제로 있었다(네트워크 로그로 확인).
  // 그래서 지금은 요청을 "체인"으로 순서대로 이어 보낸다 — 화면은 클릭마다 바로 바뀌지만,
  // 실제 서버 호출은 이전 것이 끝난 뒤에만 나가서 DB 경합 자체가 생기지 않는다.
  const onClick = () => {
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }

    hasInteracted.current = true;
    setPopping(true);
    setTimeout(() => setPopping(false), 200);

    const previousLiked = liked;
    const previousCount = count;
    const nextLiked = !previousLiked;
    setLiked(nextLiked);
    setCount(previousCount + (nextLiked ? 1 : -1));

    const requestId = ++latestRequestId.current;
    requestChain.current = requestChain.current.then(
      () => toggleShortformLike(shortformId),
      () => toggleShortformLike(shortformId), // 앞선 요청이 실패했어도 이 요청은 이어서 보낸다
    ).then(
      (result) => {
        if (latestRequestId.current !== requestId) return;
        setLiked(result.liked);
        setCount(result.likeCount);
      },
      () => {
        if (latestRequestId.current !== requestId) return;
        setLiked(previousLiked);
        setCount(previousCount);
      },
    );
  };

  // DESIGN_SPEC.md §26: right rail 아이콘 — 큰 아이콘 + 작은 label(카운트).
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-1 text-white"
      aria-label={liked ? "좋아요 취소" : "좋아요"}
    >
      <HeartIcon filled={liked} popping={popping} />
      <span className="text-[12px] font-medium">{count}</span>
    </button>
  );
}
