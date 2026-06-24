import { useEffect, useState } from "react";
import { useStore } from "./store";
import Sidebar from "./Sidebar";
import StoryCanvas from "./StoryCanvas";
import Inspector from "./Inspector";
import WritersRoom from "./WritersRoom";
import { renderShow } from "./api";

export default function App() {
  const { init, bible, dirty, busy, save, model, models, setModel, openShow } = useStore();
  const [rendering, setRendering] = useState(false);

  useEffect(() => {
    init();
  }, []);

  async function doRender() {
    if (!bible) return;
    if (dirty || !bible._slug) await save();
    const slug = useStore.getState().bible?._slug;
    if (!slug) return;
    setRendering(true);
    try {
      await renderShow(slug, bible.generateNow || 1, "line");
    } finally {
      setTimeout(() => {
        setRendering(false);
        openShow(slug); // refresh render status
      }, 4000);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="title">
          {bible ? bible.title || "Untitled" : "SHOW FACTORY"}
          {dirty && <span className="dirty">● unsaved</span>}
        </div>
        <div className="sp" />
        <select className="model" value={model} onChange={(e) => setModel(e.target.value)}>
          {models.map((m) => (
            <option key={m}>{m}</option>
          ))}
        </select>
        <button className="btn" disabled={!bible || !dirty} onClick={save}>
          SAVE
        </button>
        <button className="btn go" disabled={!bible || rendering} onClick={doRender}>
          {rendering ? "RENDERING…" : "▶ RENDER"}
        </button>
      </header>

      <div className="body">
        <Sidebar />
        <StoryCanvas />
        <div className="right">
          <div className="right-top">
            <Inspector />
          </div>
          <div className="right-bot">
            <WritersRoom />
          </div>
        </div>
      </div>

      <footer className="statusbar">
        <span className="led">█</span>
        <b>{busy || "READY"}</b>
        <span className="sp" />
        <span>MODEL: {model || "—"}</span>
        <span>{bible ? (bible.episodes || []).length + " episodes" : "no show"}</span>
      </footer>
    </div>
  );
}
