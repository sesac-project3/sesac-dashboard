// 한글 조사(은/는, 이/가, 을/를 등) 받침 유무에 따라 자동으로 붙여주는 헬퍼.
// 한글 완성형 음절은 유니코드 U+AC00~U+D7A3 범위에 (초성-11172+중성-588+종성) 공식으로
// 배열돼 있어서, 마지막 글자 코드값 % 28이 0이면 받침이 없는(모음으로 끝나는) 음절이다.
function hasBatchim(word: string): boolean {
  const lastChar = word.trim().at(-1);
  if (!lastChar) return false;
  const code = lastChar.charCodeAt(0) - 0xac00;
  if (code < 0 || code > 11171) return false; // 완성형 한글 음절이 아니면(영문/숫자 등) 판단 불가 — 받침 없다고 취급
  return code % 28 !== 0;
}

/** "한화오션" -> "한화오션은", "삼성전자" -> "삼성전자는" */
export function withTopicParticle(word: string): string {
  return `${word}${hasBatchim(word) ? "은" : "는"}`;
}

/** "한화오션" -> "한화오션이", "삼성전자" -> "삼성전자가" */
export function withSubjectParticle(word: string): string {
  return `${word}${hasBatchim(word) ? "이" : "가"}`;
}

/** "한화오션" -> "한화오션을", "삼성전자" -> "삼성전자를" */
export function withObjectParticle(word: string): string {
  return `${word}${hasBatchim(word) ? "을" : "를"}`;
}
