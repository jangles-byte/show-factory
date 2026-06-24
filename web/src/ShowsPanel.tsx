import { useState } from "react";
import { useStore } from "./store";

export default function ShowsPanel() {
  const { shows, bible, openShow, deleteShow, addEpisode, buildFromBrief, styles } = useStore();
  const [brief, setBrief] = useState("");
  const [style, setStyle] = useState("");
  const [cast, setCast] = useState(3);
  const [eps, setEps] = useState(1);
  const [lengthMin, setLengthMin] = useState(5);
  const [confirm, setConfirm] = useState<string | null>(null);

  return (
    <div className="panel">
      <div className="hd">NEW FROM BRIEF</div>
      <div className="newshow">
        <textarea
          rows={3}
          placeholder="describe a show… (e.g. a heist comedy set in a failing aquarium)"
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
        />
        <div className="row">
          <select value={style} onChange={(e) => setStyle(e.target.value)}>
            <option value="">style…</option>
            {styles.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="row">
          <label className="tiny">cast<input type="number" min={1} max={12} value={cast} onChange={(e) => setCast(+e.target.value)} /></label>
          <label className="tiny">eps<input type="number" min={1} max={20} value={eps} onChange={(e) => setEps(+e.target.value)} /></label>
          <label className="tiny">min<input type="number" min={1} max={30} value={lengthMin} onChange={(e) => setLengthMin(+e.target.value)} /></label>
        </div>
        <button
          className="go full"
          disabled={!brief.trim()}
          onClick={() => buildFromBrief(brief, { visualStyle: style || undefined, castSize: cast, generateNow: eps, episodeLengthMin: lengthMin })}
        >
          ✦ BUILD SHOW
        </button>
      </div>

      <div className="hd">LIBRARY ({shows.length})</div>
      <div className="shows">
        {shows.map((s) => (
          <div key={s.slug} className={"showrow" + (bible?._slug === s.slug ? " active" : "")}>
            <div className="showrow-main" onClick={() => openShow(s.slug)}>
              <div className="st">{s.title}</div>
              <div className="ss">
                {s.episodes} ep{s.episodes !== 1 ? "s" : ""}
                {s.rendered ? ` · ${s.rendered} rendered` : ""}
              </div>
            </div>
            {confirm === s.slug ? (
              <div className="confirm">
                <button className="mini danger" onClick={() => { deleteShow(s.slug); setConfirm(null); }}>delete</button>
                <button className="mini" onClick={() => setConfirm(null)}>keep</button>
              </div>
            ) : (
              <button className="mini danger del" title="delete show" onClick={() => setConfirm(s.slug)}>✕</button>
            )}
          </div>
        ))}
        {shows.length === 0 && <div className="hint">no shows yet — build one above</div>}
      </div>

      <div className="spacer" />
      {bible && (
        <button className="ghost full" onClick={addEpisode}>
          + ADD EPISODE
        </button>
      )}
    </div>
  );
}
