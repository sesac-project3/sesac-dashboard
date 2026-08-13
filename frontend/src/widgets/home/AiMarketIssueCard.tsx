"use client";

import Card from "@/shared/ui/Card";

interface AiMarketIssueCardProps {
  title: string;
  text: string;
  timestamp: string;
}

export default function AiMarketIssueCard({
  title,
  text,
  timestamp,
}: AiMarketIssueCardProps) {
  return (
    <Card className="group relative overflow-hidden bg-gradient-to-br from-purple-50/70 via-indigo-50/40 to-pink-50/60 dark:from-purple-950/20 dark:via-indigo-950/20 dark:to-pink-950/20">
      <div className="flex items-center gap-2">
        <h3 className="text-[17px] font-bold text-heading">{title}</h3>
        <span className="rounded-full bg-purple-600/10 px-2 py-0.5 text-[11px] font-semibold text-purple-600 dark:bg-purple-400/20 dark:text-purple-300">
          AI{" "}
          <span className="inline-block transition-transform duration-500 ease-out group-hover:rotate-[360deg]">
            ✦
          </span>
        </span>
      </div>

      <p className="mt-3 text-[14px] leading-relaxed text-heading/90 line-clamp-3">
        {text}
      </p>

      <p className="mt-3 text-[11px] font-medium text-caption">{timestamp}</p>
    </Card>
  );
}
