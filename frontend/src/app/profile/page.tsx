"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useLoggedIn } from "@/shared/hooks/useLoggedIn";
import { logout } from "@/shared/api/auth";
import PageContainer from "@/shared/ui/PageContainer";
import Card from "@/shared/ui/Card";
import {
  getTelegramStatus,
  generateTelegramLinkCode,
  type TelegramStatusResponse,
} from "@/shared/api/telegram";

export default function ProfilePage() {
  const router = useRouter();
  const loggedIn = useLoggedIn();

  const [tgStatus, setTgStatus] = useState<TelegramStatusResponse | null>(null);
  const [linkCode, setLinkCode] = useState<string | null>(null);
  const [isLinking, setIsLinking] = useState(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (loggedIn === false) {
      router.replace("/login");
    }
  }, [loggedIn, router]);

  // Fetch Telegram link status on load
  useEffect(() => {
    if (!loggedIn) return;

    getTelegramStatus()
      .then((status) => {
        setTgStatus(status);
      })
      .catch((err) => {
        console.error("Failed to load Telegram status", err);
      });

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [loggedIn]);

  // Start polling to detect successful linkage automatically
  const startPolling = () => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(() => {
      getTelegramStatus()
        .then((status) => {
          if (status.linked) {
            setTgStatus(status);
            setLinkCode(null);
            setIsLinking(false);
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
          }
        })
        .catch(() => {});
    }, 3000);
  };

  const handleStartLink = async () => {
    if (isLinking) return;
    setIsLinking(true);

    try {
      const data = await generateTelegramLinkCode();
      setLinkCode(data.linkCode);

      // Construct Telegram deep link with start parameter
      const botUrl = `https://t.me/${data.botUsername}?start=${data.linkCode}`;
      
      // Open in a new tab/window
      window.open(botUrl, "_blank");

      // Start checking if linking succeeds in background
      startPolling();
    } catch (err) {
      console.error("Failed to generate link code", err);
      alert("인증 코드 생성에 실패했습니다. 다시 시도해 주세요.");
      setIsLinking(false);
    }
  };

  if (!loggedIn) return null;

  return (
    <PageContainer>
      <h1 className="my-4 text-[18px] font-semibold text-heading">내 정보</h1>
      
      <div className="flex flex-col gap-4">
        {/* Account Info */}
        <Card className="flex flex-col gap-1">
          <p className="text-[14px] font-medium text-heading">카카오 계정으로 로그인됨</p>
          <p className="text-[13px] text-caption">서비스를 이용해주셔서 감사합니다.</p>
        </Card>

        {/* Telegram Integration Card */}
        <Card className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[15px] font-bold text-heading flex items-center gap-2">
              <span>✈️</span> 텔레그램 알림 서비스
            </h3>
            {tgStatus?.linked ? (
              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700">
                연동 완료
              </span>
            ) : (
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-semibold text-slate-500">
                미연동
              </span>
            )}
          </div>

          <p className="text-[13px] leading-relaxed text-caption">
            {tgStatus?.linked
              ? "현재 텔레그램 계정과 정상적으로 연동되어 있습니다. 실시간 시세 등락 알림 및 매일 투자 요약 브리핑을 메시지로 보내드립니다."
              : "실시간 주가 급변 경보(±5% 돌파 시) 및 매일 장 전/후 투자 브리핑을 텔레그램 메시지로 바로 받아보실 수 있습니다."}
          </p>

          {!tgStatus?.linked && (
            <div className="mt-1 flex flex-col gap-2">
              {linkCode ? (
                <div className="flex flex-col items-center gap-2 rounded-xl bg-slate-50 p-3.5 text-center border border-border/40">
                  <span className="text-[12px] text-caption font-medium">발급된 연동 코드 (10분 유효)</span>
                  <span className="text-[20px] font-black tracking-wider text-heading">{linkCode}</span>
                  <p className="text-[11px] text-caption">
                    텔레그램 대화방에서 시작을 누르거나 대화가 중단된 경우 발급된 코드를 다시 입력해 주세요.
                  </p>
                  <button
                    onClick={() => {
                      const botUrl = `https://t.me/${tgStatus?.botUsername || "bot"}?start=${linkCode}`;
                      window.open(botUrl, "_blank");
                    }}
                    className="mt-2 text-[13px] font-semibold text-primary underline"
                  >
                    텔레그램 봇으로 이동하기
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleStartLink}
                  disabled={isLinking}
                  className="flex h-[42px] w-full items-center justify-center rounded-lg bg-primary text-[14px] font-semibold text-white transition hover:bg-primary-hover active:scale-[0.98]"
                >
                  {isLinking ? "코드 생성 중..." : "알림 연동 시작하기"}
                </button>
              )}
            </div>
          )}
        </Card>

        {/* Logout */}
        <button
          onClick={logout}
          className="mt-2 flex h-[52px] w-full items-center justify-center rounded-full border border-border text-[15px] font-medium text-danger transition active:scale-[0.98]"
        >
          로그아웃
        </button>
      </div>
    </PageContainer>
  );
}
