import { useEffect, useState } from "react";
import { useStore } from "./store";

const SIZES = [
  { id: "landscape", label: "16:9 · 1280×720" },
  { id: "portrait", label: "2:3 · 832×1216" },
  { id: "square", label: "1:1 · 1024×1024" },
];

export default function PlaygroundPanel() {
  const { styles, comfyModels, pgImages, pgBusy, pgError, loadComfyModels, generateImage } = useStore();
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("");
  const [checkpoint, setCheckpoint] = useState("");
  const [lora, setLora] = useState("");
  const [loraWeight, setLoraWeight] = useState(0.75);
  const [size, setSize] = useState("landscape");
  const [seed, setSeed] = useState("");

  useEffect(() => { loadComfyModels(); }, []);
  useEffect(() => {
    if (comfyModels && !checkpoint) setCheckpoint(comfyModels.default || comfyModels.checkpoints[0] || "");
  }, [comfyModels]);

  const up = comfyModels?.up;

  function go() {
    generateImage({ prompt, style, checkpoint, lora: lora || null, lora_weight: loraWeight, size, seed });
  }

  return (
    <div className="panel">
      <div className="hd">
        IMAGE PLAYGROUND
        <span className={"comfy-dot " + (up ? "on" : "off")} title={up ? "ComfyUI running" : "ComfyUI offline"} />
      </div>

      {comfyModels && !up && (
        <div className="errbox">ComfyUI is offline. Start it, then <a onClick={() => loadComfyModels()}>recheck</a>.</div>
      )}

      <div className="pgform">
        <label className="tiny">PROMPT
          <textarea rows={3} placeholder="a fox detective in a rainy alley, neon signs"
            value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </label>

        <label className="tiny">STYLE (optional)
          <select value={style} onChange={(e) => setStyle(e.target.value)}>
            <option value="">— none —</option>
            {styles.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>

        <label className="tiny">MODEL (checkpoint)
          <select value={checkpoint} onChange={(e) => setCheckpoint(e.target.value)}>
            {(comfyModels?.checkpoints || []).map((c) => <option key={c}>{c}</option>)}
            {comfyModels && comfyModels.checkpoints.length === 0 && <option value="">no checkpoints found</option>}
          </select>
        </label>

        <div className="row">
          <label className="tiny" style={{ flex: 2 }}>LoRA (optional)
            <select value={lora} onChange={(e) => setLora(e.target.value)}>
              <option value="">— none —</option>
              {(comfyModels?.loras || []).map((l) => <option key={l}>{l}</option>)}
            </select>
          </label>
          <label className="tiny" style={{ flex: 1, opacity: lora ? 1 : 0.4 }}>WEIGHT
            <input type="number" step={0.05} min={0} max={1.5} value={loraWeight}
              disabled={!lora} onChange={(e) => setLoraWeight(+e.target.value)} />
          </label>
        </div>

        <div className="row">
          <label className="tiny" style={{ flex: 2 }}>SIZE
            <select value={size} onChange={(e) => setSize(e.target.value)}>
              {SIZES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </label>
          <label className="tiny" style={{ flex: 1 }}>SEED
            <input placeholder="random" value={seed} onChange={(e) => setSeed(e.target.value.replace(/[^0-9]/g, ""))} />
          </label>
        </div>

        <button className="go full" disabled={pgBusy || !prompt.trim() || !up} onClick={go}>
          {pgBusy ? "● GENERATING…" : "❖ GENERATE"}
        </button>
        {pgError && <div className="errbox">{pgError}</div>}
      </div>

      <div className="pggrid">
        {pgImages.map((im) => (
          <div className="pgitem" key={im.url}>
            <a href={im.url} target="_blank" rel="noreferrer"><img src={im.url} alt={im.prompt} /></a>
            <div className="pgmeta">
              <span className="pgseed" title="reuse this seed" onClick={() => setSeed(String(im.seed))}>
                seed {im.seed}
              </span>
              <a className="pgdl" href={im.url} download title="download">↓</a>
            </div>
          </div>
        ))}
        {pgImages.length === 0 && <div className="hint">generated images appear here.</div>}
      </div>
    </div>
  );
}
