import { useRef } from "react";
import { useStore } from "./store";
import type { CharacterAsset } from "./types";

function readAsDataURL(file: File): Promise<{ name: string; dataUrl: string }> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve({ name: file.name, dataUrl: String(r.result) });
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

function CharacterCard({ c }: { c: CharacterAsset }) {
  const { charBusy, uploadCharacterRefs, lockCharacter, deleteCharacterRef } = useStore();
  const fileRef = useRef<HTMLInputElement>(null);
  const busy = charBusy === c.name;
  const locked = !!c.portrait;

  async function onFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const imgs = await Promise.all(Array.from(files).map(readAsDataURL));
    await uploadCharacterRefs(c.name, imgs);
  }

  return (
    <div className="ccard">
      <div className="ccard-top">
        <div className={"portrait" + (locked ? "" : " empty")}>
          {locked ? <img src={c.portrait!} alt={c.name} /> : <span>no portrait</span>}
          {c.instantid && <span className="badge" title="reference face locked (InstantID)">ID</span>}
        </div>
        <div className="cmeta">
          <b>{c.name}</b>
          <span className="sub">{c.gender !== "?" ? c.gender + " · " : ""}{c.role}</span>
          {c.voice && <span className="sub">voice: {c.voice}</span>}
          {c.look && <p className="look">{c.look}</p>}
        </div>
      </div>

      <div className="refs">
        {c.refs.map((r) => (
          <div className="ref" key={r}>
            <img src={r} alt="ref" />
            <button className="x" title="remove" onClick={() => deleteCharacterRef(c.name, r.split("/").pop() || r)}>✕</button>
          </div>
        ))}
        <button className="ref add" onClick={() => fileRef.current?.click()} title="add reference photos">
          ＋
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => { onFiles(e.target.files); e.target.value = ""; }}
        />
      </div>

      <button className={"go full" + (busy ? " busy" : "")} disabled={busy} onClick={() => lockCharacter(c.name)}>
        {busy ? "● RENDERING…" : locked ? "↻ RE-LOCK PORTRAIT" : c.refs.length ? "🔒 LOCK (InstantID)" : "🔒 LOCK CHARACTER"}
      </button>
    </div>
  );
}

export default function CharactersPanel() {
  const { bible, characters, charError, styles, setBible } = useStore();

  if (!bible) {
    return (
      <div className="panel">
        <div className="hd">CAST</div>
        <div className="hint">open a show in the SHOWS tab to design its cast.</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="hd">CAST — {bible.title}</div>
      <div className="cast-style">
        <label className="tiny" style={{ width: "100%" }}>
          ANIMATION STYLE (applied when you lock)
          <select value={bible.visualStyle || ""} onChange={(e) => setBible({ ...bible, visualStyle: e.target.value })}>
            <option value="">— undecided —</option>
            {styles.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="hint small">
        Upload a few photos of the real person → Lock → ComfyUI renders a portrait in your style with that face
        (InstantID). Locking needs ComfyUI running.
      </div>

      {charError && <div className="errbox">{charError}</div>}

      <div className="cards">
        {characters.map((c) => (
          <CharacterCard key={c.name} c={c} />
        ))}
        {characters.length === 0 && <div className="hint">this show has no cast yet — add some in the writers' room.</div>}
      </div>
    </div>
  );
}
