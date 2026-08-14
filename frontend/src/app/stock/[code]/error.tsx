"use client";

import Button from "@/shared/ui/Button";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 p-8 text-center">
      <p className="text-[14px] text-caption">
        종목 정보를 불러오지 못했어요.
        <br />
        잠시 후 다시 시도해주세요.
      </p>
      <Button
        onClick={reset}
      >
        다시 시도
      </Button>
    </div>
  );
}
