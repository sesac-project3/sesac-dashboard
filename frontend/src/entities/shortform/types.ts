export interface Shortform {
  id: number;
  stockCode: string;
  stockName: string;
  sentiment: "POS" | "NEG";
  videoUrl: string;
  subtitleText: string;
  aiInsight: string | null;
  likeCount: number;
  viewCount: number;
  liked: boolean;
}
