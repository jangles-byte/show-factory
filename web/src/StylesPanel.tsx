import { useEffect, useState } from "react";
import { useStore } from "./store";
import type { StyleDef } from "./types";

const BLANK: StyleDef = { name: "New style", prompt: "", negative: "", lora: null, lora_weight: 0.75 };

export default function StylesPanel() {
  const { styleDefs, loadStyleDefs, saveStyleDefs, busy } = useStore();
  const [defs, setDefs] = useState<StyleDef[]>([]);
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => { loadStyleDefs(); }, []);
  useEffect(() => { setDefs(styleDefs); }, [styleDefs]);

  const dirty = JSON.stringify(defs) !== JSON.stringify(styleDefs);

  const patch = (i: number, p: Partial<StyleDef>) =>
    setDefs(defs.map((d, j) => (j === i ? { ...d, ...p } : d)));
  const add = () => { setDefs([...defs, { ...BLANK }]); setOpen(defs.length); };
  const remove = (i: number) => { setDefs(defs.filter((_, j) => j !== i)); setOpen(null); };

  return (
    <div className="panel">
      <div className="hd">ART STYLES ({defs.length})</div>
      <div className="hint small">
        Each style is appended to every image. Drop an SDXL LoRA <code>.safetensors</code> into
        <code> ~/Desktop/ComfyUI/models/loras/</code> and name it below.{" "}
        <a href="https://civitai.com/models?types=LORA&baseModels=SDXL%201.0" target="_blank" rel="noreferrer">
          Browse LoRAs on Civitai ↗
        </a>
      </div>

      <div className="stylelist">
        {defs.map((d, i) => (
          <div className={"stylecard" + (open === i ? " open" : "")} key={i}>
            <div className="stylehead" onClick={() => setOpen(open === i ? null : i)}>
              <span className="sname">{d.name || "—"}</span>
              {d.lora && <span className="lorab" title={d.lora}>LoRA</span>}
              <span className="chev">{open === i ? "▾" : "▸"}</span>
            </div>
            {open === i && (
              <div className="stylebody">
                <label className="tiny">NAME
                  <input value={d.name} onChange={(e) => patch(i, { name: e.target.value })} />
                </label>
                <label className="tiny">PROMPT (style description)
                  <textarea rows={4} value={d.prompt} onChange={(e) => patch(i, { prompt: e.target.value })} />
                </label>
                <label className="tiny">NEGATIVE (optional)
                  <textarea rows={2} value={d.negative || ""} onChange={(e) => patch(i, { negative: e.target.value })} />
                </label>
                <div className="row">
                  <label className="tiny" style={{ flex: 2 }}>LoRA FILE (optional)
                    <input placeholder="archer_style.safetensors" value={d.lora || ""}
                      onChange={(e) => patch(i, { lora: e.target.value || null })} />
                  </label>
                  <label className="tiny" style={{ flex: 1 }}>WEIGHT
                    <input type="number" step={0.05} min={0} max={1.5} value={d.lora_weight ?? 0.75}
                      onChange={(e) => patch(i, { lora_weight: +e.target.value })} />
                  </label>
                </div>
                <button className="mini danger" onClick={() => remove(i)}>delete style</button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="spacer" />
      <div className="stylefoot">
        <button className="ghost" onClick={add}>+ ADD STYLE</button>
        <button className="go" disabled={!dirty || !!busy} onClick={() => saveStyleDefs(defs)}>
          {busy ? "…" : "SAVE STYLES"}
        </button>
      </div>
    </div>
  );
}
