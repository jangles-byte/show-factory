import type { Bible, ShowSummary, StyleDef, CharacterAsset, RenderItem } from "./types";

const json = (r: Response) => r.json();
const enc = encodeURIComponent;
const post = (url: string, body: any) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(json);

export const listShows = (): Promise<ShowSummary[]> => fetch("/shows").then(json).then((d) => d.shows || []);
export const getShow = (slug: string): Promise<Bible> => fetch("/show?slug=" + enc(slug)).then(json);
export const saveShow = (bible: Bible) => post("/save", bible);
export const buildShow = (brief: string, prefs: any) => post("/build", { brief, prefs });
export const renderShow = (slug: string, episodes: number, shots: string) => post("/render", { slug, episodes, shots });
export const deleteShow = (slug: string) => post("/show/delete", { slug });
export const getStyles = (): Promise<string[]> => fetch("/styles").then(json).then((d) => d.styles || []);

// --- styles (full editing) ---
export const getStylesFull = (): Promise<StyleDef[]> => fetch("/styles/full").then(json).then((d) => d.styles || []);
export const saveStyles = (styles: StyleDef[]) => post("/styles/save", { styles });

// --- characters ---
export interface CharacterPack { slug: string; title: string; style: string; characters: CharacterAsset[]; }
export const listCharacters = (slug: string): Promise<CharacterPack> =>
  fetch("/characters?slug=" + enc(slug)).then(json);
export const uploadRefs = (slug: string, character: string, images: { name: string; dataUrl: string }[]) =>
  post("/characters/upload", { slug, character, images });
export const lockCharacter = (slug: string, character: string) =>
  post("/characters/lock", { slug, character });
export const deleteRef = (slug: string, character: string, file: string) =>
  post("/characters/delete-ref", { slug, character, file });

// --- renders ---
export const listRenders = (): Promise<RenderItem[]> => fetch("/renders").then(json).then((d) => d.renders || []);
export const listModels = async (): Promise<string[]> => {
  try {
    const d = await fetch("/api/tags").then(json);
    return (d.models || []).map((m: any) => m.name);
  } catch {
    return [];
  }
};

export async function* chatStream(messages: any[], model: string) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, messages, stream: true, options: { temperature: 0.8 } }),
  });
  if (!res.body) return;
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const j = JSON.parse(line);
        if (j.message?.content) yield j.message.content as string;
      } catch {
        /* ignore partial */
      }
    }
  }
}
