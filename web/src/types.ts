export interface Character {
  name: string;
  role?: string;
  personality?: string;
  wants?: string;
  secret?: string;
  gender?: string;
}

export interface Episode {
  number?: number;
  title?: string;
  premise?: string;
  beats?: string[];
}

export interface Bible {
  title?: string;
  logline?: string;
  genre?: string;
  tone?: string;
  visualStyle?: string;
  setting?: string;
  mode?: string;
  episodeLengthMin?: number;
  episodesPerSeason?: number;
  generateNow?: number;
  episodeEngine?: string;
  seasonArc?: string;
  cast?: Character[];
  episodes?: Episode[];
  _slug?: string;
  _status?: Record<string, string>;
}

export interface ShowSummary {
  slug: string;
  title: string;
  episodes: number;
  rendered: number;
}

export interface StyleDef {
  name: string;
  prompt: string;
  negative?: string;
  lora?: string | null;
  lora_weight?: number;
}

export interface CharacterAsset {
  name: string;
  role: string;
  personality: string;
  gender: string;
  look: string;
  seed: number | null;
  voice: string;
  instantid: boolean;
  refs: string[];
  portrait: string | null;
}

export interface RenderItem {
  slug: string;
  show: string;
  ep: string;
  url: string;
}

export interface ComfyModels {
  checkpoints: string[];
  loras: string[];
  default: string;
  up: boolean;
}

export interface PgResult {
  url: string;
  seed: number;
  checkpoint: string;
  lora: string | null;
  prompt: string;
}
