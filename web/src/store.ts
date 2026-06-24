import { create } from "zustand";
import type { Bible, Episode, ShowSummary, StyleDef, CharacterAsset, RenderItem } from "./types";
import * as api from "./api";

export type LeftTab = "shows" | "characters" | "styles" | "renders";

interface State {
  shows: ShowSummary[];
  bible: Bible | null;
  selected: string | null; // "season" | "ep-<idx>" | null
  model: string;
  models: string[];
  styles: string[];
  dirty: boolean;
  busy: string;

  leftTab: LeftTab;
  characters: CharacterAsset[];
  charBusy: string; // name currently locking, "" if idle
  charError: string;
  styleDefs: StyleDef[];
  renders: RenderItem[];

  init: () => Promise<void>;
  loadShows: () => Promise<void>;
  openShow: (slug: string) => Promise<void>;
  deleteShow: (slug: string) => Promise<void>;
  setBible: (b: Bible) => void;
  updateEpisode: (idx: number, patch: Partial<Episode>) => void;
  addEpisode: () => void;
  removeEpisode: (idx: number) => void;
  moveEpisode: (idx: number, dir: -1 | 1) => void;
  select: (id: string | null) => void;
  save: () => Promise<void>;
  buildFromBrief: (brief: string, prefs: any) => Promise<void>;
  setModel: (m: string) => void;

  setLeftTab: (t: LeftTab) => void;
  loadCharacters: () => Promise<void>;
  uploadCharacterRefs: (name: string, images: { name: string; dataUrl: string }[]) => Promise<void>;
  lockCharacter: (name: string) => Promise<void>;
  deleteCharacterRef: (name: string, file: string) => Promise<void>;
  loadStyleDefs: () => Promise<void>;
  saveStyleDefs: (defs: StyleDef[]) => Promise<void>;
  loadRenders: () => Promise<void>;
}

export const useStore = create<State>((set, get) => ({
  shows: [],
  bible: null,
  selected: null,
  model: "",
  models: [],
  styles: [],
  dirty: false,
  busy: "",

  leftTab: "shows",
  characters: [],
  charBusy: "",
  charError: "",
  styleDefs: [],
  renders: [],

  async init() {
    const [shows, models, styles] = await Promise.all([api.listShows(), api.listModels(), api.getStyles()]);
    const model = models.find((m) => m.includes("gemma4:e2b")) || models[0] || "";
    set({ shows, models, styles, model });
  },
  async loadShows() {
    set({ shows: await api.listShows() });
  },
  async openShow(slug) {
    set({ busy: "loading…" });
    const bible = await api.getShow(slug);
    set({ bible, selected: "season", dirty: false, busy: "", characters: [], charError: "" });
    if (get().leftTab === "characters") get().loadCharacters();
  },
  async deleteShow(slug) {
    set({ busy: "deleting…" });
    await api.deleteShow(slug);
    const cur = get().bible;
    const clear = cur?._slug === slug;
    set({
      busy: "",
      ...(clear ? { bible: null, selected: null, characters: [], dirty: false } : {}),
    });
    await get().loadShows();
  },
  setBible(b) {
    set({ bible: b, dirty: true });
  },
  updateEpisode(idx, patch) {
    const b = get().bible;
    if (!b) return;
    const episodes = [...(b.episodes || [])];
    episodes[idx] = { ...episodes[idx], ...patch };
    set({ bible: { ...b, episodes }, dirty: true });
  },
  addEpisode() {
    const b = get().bible;
    if (!b) return;
    const episodes = [...(b.episodes || [])];
    episodes.push({ number: episodes.length + 1, title: "New Episode", premise: "", beats: [] });
    set({ bible: { ...b, episodes }, dirty: true, selected: "ep-" + (episodes.length - 1) });
  },
  removeEpisode(idx) {
    const b = get().bible;
    if (!b) return;
    const episodes = (b.episodes || []).filter((_, i) => i !== idx).map((e, i) => ({ ...e, number: i + 1 }));
    set({ bible: { ...b, episodes }, dirty: true, selected: "season" });
  },
  moveEpisode(idx, dir) {
    const b = get().bible;
    if (!b) return;
    const episodes = [...(b.episodes || [])];
    const j = idx + dir;
    if (j < 0 || j >= episodes.length) return;
    [episodes[idx], episodes[j]] = [episodes[j], episodes[idx]];
    episodes.forEach((e, i) => (e.number = i + 1));
    set({ bible: { ...b, episodes }, dirty: true, selected: "ep-" + j });
  },
  select(id) {
    set({ selected: id });
  },
  async save() {
    const b = get().bible;
    if (!b) return;
    set({ busy: "saving…" });
    const r = await api.saveShow(b);
    set({ bible: { ...b, _slug: r.slug || b._slug }, dirty: false, busy: "" });
    await get().loadShows();
  },
  async buildFromBrief(brief, prefs) {
    set({ busy: "writing bible…" });
    const r = await api.buildShow(brief, prefs);
    set({ busy: "" });
    if (r.bible) {
      set({ bible: { ...r.bible, _slug: r.bible._slug }, selected: "season", dirty: false });
      await get().loadShows();
    }
  },
  setModel(m) {
    set({ model: m });
  },

  setLeftTab(t) {
    set({ leftTab: t });
    if (t === "characters" && get().bible?._slug && get().characters.length === 0) get().loadCharacters();
    if (t === "styles" && get().styleDefs.length === 0) get().loadStyleDefs();
    if (t === "renders") get().loadRenders();
  },

  async loadCharacters() {
    const slug = get().bible?._slug;
    if (!slug) {
      set({ characters: [] });
      return;
    }
    set({ charError: "" });
    try {
      const pack = await api.listCharacters(slug);
      set({ characters: pack.characters || [] });
    } catch (e: any) {
      set({ charError: String(e) });
    }
  },
  async uploadCharacterRefs(name, images) {
    const slug = get().bible?._slug;
    if (!slug || images.length === 0) return;
    set({ charBusy: name, charError: "" });
    try {
      await api.uploadRefs(slug, name, images);
      await get().loadCharacters();
    } catch (e: any) {
      set({ charError: String(e) });
    } finally {
      set({ charBusy: "" });
    }
  },
  async lockCharacter(name) {
    if (get().dirty) await get().save(); // lock reads the bible from disk
    const slug = get().bible?._slug;
    if (!slug) return;
    set({ charBusy: name, charError: "", busy: "locking " + name + "…" });
    try {
      const r = await api.lockCharacter(slug, name);
      if (r.error) set({ charError: r.error });
      await get().loadCharacters();
    } catch (e: any) {
      set({ charError: String(e) });
    } finally {
      set({ charBusy: "", busy: "" });
    }
  },
  async deleteCharacterRef(name, file) {
    const slug = get().bible?._slug;
    if (!slug) return;
    await api.deleteRef(slug, name, file);
    await get().loadCharacters();
  },

  async loadStyleDefs() {
    set({ styleDefs: await api.getStylesFull() });
  },
  async saveStyleDefs(defs) {
    set({ busy: "saving styles…" });
    await api.saveStyles(defs);
    const styles = await api.getStyles();
    set({ styleDefs: defs, styles, busy: "" });
  },

  async loadRenders() {
    set({ renders: await api.listRenders() });
  },
}));
