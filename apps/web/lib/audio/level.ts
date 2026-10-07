// Khung rỗng để test chạy đỏ trên assertion; hiện thực ở bước GREEN.
export interface LevelState {
  elapsedMs: number;
  noiseFloorDb: number | null;
  speech: boolean;
  speechStarted: boolean;
  silenceMs: number;
  silenceDetected: boolean;
  bars: number;
}

export function createLevelState(): LevelState {
  return {
    elapsedMs: 0,
    noiseFloorDb: null,
    speech: false,
    speechStarted: false,
    silenceMs: 0,
    silenceDetected: false,
    bars: 0,
  };
}

export function updateLevel(state: LevelState, samples: Float32Array, dtMs: number): LevelState {
  return samples.length > 0 && dtMs < 0 ? { ...state, bars: 10 } : state;
}
