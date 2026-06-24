import { Handle, Position } from "@xyflow/react";

export function SeasonNode({ data }: any) {
  const b = data.bible;
  return (
    <div className="node season">
      <div className="nh">SEASON</div>
      <div className="nt">{b.title || "Untitled"}</div>
      <div className="nm">
        {(b.episodes || []).length} episodes · {b.genre || "—"}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export function EpisodeNode({ data, selected }: any) {
  const ep = data.ep;
  return (
    <div className={"node episode" + (selected ? " sel" : "")}>
      <Handle type="target" position={Position.Left} />
      <div className="nh">
        EP {ep.number ?? data.idx + 1}
        {data.status ? <span className="dot" title="rendered">●</span> : null}
      </div>
      <div className="nt">{ep.title || "Untitled"}</div>
      <div className="nm">{(ep.premise || "").slice(0, 90)}</div>
    </div>
  );
}
