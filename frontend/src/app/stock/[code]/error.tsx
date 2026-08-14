"use client";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 p-8 text-center">
      <p className="text-[14px] text-caption">
        종목 정보를 불러오지 못했어요.
        <br />
        잠시 후 다시 시도해주세요.
      </p>
      <button
        type="button"
        onClick={reset}
        className="rounded-sm bg-primary px-5 py-2.5 text-[14px] font-medium text-white"
      >
        다시 시도
      </button>
    </div>
  );
}
