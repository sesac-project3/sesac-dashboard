export interface Shortform {
  id: number;
  stockCode: string;
  stockName: string;
  sentiment: "긍정" | "부정";
  videoUrl: string;
  subtitleText: string;
  aiInsight: string | null;
  likeCount: number;
  viewCount: number;
}
