// 숏폼 영상들이 공유하는 볼륨 설정. ShortformCard는 스크롤로 다음 영상으로 넘어갈 때마다
// 새 <video> 엘리먼트로 다시 mount되는데, 그때마다 볼륨이 기본값으로 돌아가면 안 되니까
// 컴포넌트 state가 아니라 모듈 스코프에 하나만 둔다(videoPositionStore.ts와 같은 패턴).
// localStorage에도 저장해서 새로고침/다음 방문에도 유지한다.
const VOLUME_KEY = "shortform:volume";
const MUTED_KEY = "shortform:muted";

export interface VolumeState {
  volume: number; // 0~1
  muted: boolean;
}

const DEFAULT_STATE: VolumeState = { volume: 1, muted: true }; // 브라우저 자동재생 정책 때문에 기본은 muted

function readInitialState(): VolumeState {
  if (typeof window === "undefined") return DEFAULT_STATE;
  const storedVolume = Number(window.localStorage.getItem(VOLUME_KEY));
  const storedMuted = window.localStorage.getItem(MUTED_KEY);
  return {
    volume: Number.isFinite(storedVolume) && storedVolume >= 0 && storedVolume <= 1 ? storedVolume : DEFAULT_STATE.volume,
    muted: storedMuted === null ? DEFAULT_STATE.muted : storedMuted === "1",
  };
}

let state = readInitialState();
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

export function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot(): VolumeState {
  return state;
}

export function getServerSnapshot(): VolumeState {
  return DEFAULT_STATE;
}

export function setVolume(volume: number) {
  const clamped = Math.min(1, Math.max(0, volume));
  // 슬라이더를 0까지 내리면 음소거로, 0보다 크게 올리면 음소거 해제로 — 볼륨과 음소거
  // 상태가 따로 놀면(예: 음소거인데 슬라이더는 50%) 사용자가 헷갈린다.
  state = { volume: clamped, muted: clamped === 0 };
  window.localStorage.setItem(VOLUME_KEY, String(clamped));
  window.localStorage.setItem(MUTED_KEY, state.muted ? "1" : "0");
  emit();
}

export function setMuted(muted: boolean) {
  state = { ...state, muted };
  window.localStorage.setItem(MUTED_KEY, muted ? "1" : "0");
  emit();
}
