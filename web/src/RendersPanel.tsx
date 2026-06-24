import { useEffect, useState } from "react";
import { useStore } from "./store";

export default function RendersPanel() {
  const { renders, loadRenders, openShow } = useStore();
  const [playing, setPlaying] = useState<string | null>(null);

  useEffect(() => { loadRenders(); }, []);

  return (
    <div className="panel">
      <div className="hd">FINISHED EPISODES ({renders.length})</div>
      <button className="ghost full" onClick={() => loadRenders()}>↻ REFRESH</button>

      <div className="gallery">
        {renders.map((r) => {
          const id = r.url;
          return (
            <div className="gitem" key={id}>
              {playing === id ? (
                <video src={r.url} controls autoPlay style={{ width: "100%" }} />
              ) : (
                <div className="gthumb" onClick={() => setPlaying(id)}>
                  <video src={r.url + "#t=1"} preload="metadata" />
                  <span className="play">▶</span>
                </div>
              )}
              <div className="grow">
                <div>
                  <div className="gtitle">{r.show}</div>
                  <div className="gsub">{r.ep}</div>
                </div>
                <button className="mini" onClick={() => openShow(r.slug)}>open</button>
              </div>
            </div>
          );
        })}
        {renders.length === 0 && <div className="hint">no rendered episodes yet — hit ▶ RENDER on a show.</div>}
      </div>
    </div>
  );
}
