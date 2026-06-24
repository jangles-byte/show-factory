import { useStore } from "./store";

function Field({ label, children }: any) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

export default function Inspector() {
  const { bible, selected, styles, setBible, updateEpisode, removeEpisode, moveEpisode } = useStore();

  if (!bible) return <div className="inspector empty">— open or create a show —</div>;

  // ---- SEASON / show meta ----
  if (!selected || selected === "season") {
    const set = (k: string, v: any) => setBible({ ...bible, [k]: v });
    return (
      <div className="inspector">
        <div className="ihead">[ SEASON ]</div>
        <Field label="TITLE">
          <input value={bible.title || ""} onChange={(e) => set("title", e.target.value)} />
        </Field>
        <Field label="LOGLINE">
          <textarea rows={3} value={bible.logline || ""} onChange={(e) => set("logline", e.target.value)} />
        </Field>
        <div className="row">
          <Field label="GENRE">
            <input value={bible.genre || ""} onChange={(e) => set("genre", e.target.value)} />
          </Field>
          <Field label="TONE">
            <input value={bible.tone || ""} onChange={(e) => set("tone", e.target.value)} />
          </Field>
        </div>
        <Field label="VISUAL STYLE">
          <select value={bible.visualStyle || ""} onChange={(e) => set("visualStyle", e.target.value)}>
            <option value="">— undecided —</option>
            {styles.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </Field>
        <Field label="SETTING">
          <input value={bible.setting || ""} onChange={(e) => set("setting", e.target.value)} />
        </Field>
        <div className="row">
          <Field label="EP LENGTH (min)">
            <input type="number" value={bible.episodeLengthMin ?? 5} onChange={(e) => set("episodeLengthMin", +e.target.value)} />
          </Field>
          <Field label="EPS / SEASON">
            <input type="number" value={bible.episodesPerSeason ?? 8} onChange={(e) => set("episodesPerSeason", +e.target.value)} />
          </Field>
        </div>
        <Field label="EPISODE ENGINE">
          <textarea rows={2} value={bible.episodeEngine || ""} onChange={(e) => set("episodeEngine", e.target.value)} />
        </Field>
        <Field label="SEASON ARC">
          <textarea rows={3} value={bible.seasonArc || ""} onChange={(e) => set("seasonArc", e.target.value)} />
        </Field>
        <div className="ihead" style={{ marginTop: 18 }}>CAST</div>
        {(bible.cast || []).map((c, i) => (
          <div className="castrow" key={i}>
            <b>{c.name}</b>
            <span>{c.gender || "?"} · {c.role}</span>
          </div>
        ))}
      </div>
    );
  }

  // ---- EPISODE ----
  const idx = parseInt(selected.replace("ep-", ""), 10);
  const ep = (bible.episodes || [])[idx];
  if (!ep) return <div className="inspector empty">—</div>;
  const rendered = bible._status?.["ep" + String(ep.number ?? idx + 1).padStart(2, "0")];

  return (
    <div className="inspector">
      <div className="ihead">
        [ EPISODE {ep.number ?? idx + 1} ]
        <span className="ispacer" />
        <button className="mini" onClick={() => moveEpisode(idx, -1)}>↑</button>
        <button className="mini" onClick={() => moveEpisode(idx, 1)}>↓</button>
        <button className="mini danger" onClick={() => removeEpisode(idx)}>✕</button>
      </div>
      <Field label="TITLE">
        <input value={ep.title || ""} onChange={(e) => updateEpisode(idx, { title: e.target.value })} />
      </Field>
      <Field label="PREMISE">
        <textarea rows={4} value={ep.premise || ""} onChange={(e) => updateEpisode(idx, { premise: e.target.value })} />
      </Field>
      <Field label="BEATS (one per line)">
        <textarea
          rows={6}
          value={(ep.beats || []).join("\n")}
          onChange={(e) => updateEpisode(idx, { beats: e.target.value.split("\n").filter((x) => x.trim()) })}
        />
      </Field>
      {rendered && (
        <div className="field">
          <label>RENDERED</label>
          <video src={rendered} controls style={{ width: "100%", border: "1px solid var(--line2)" }} />
        </div>
      )}
    </div>
  );
}
