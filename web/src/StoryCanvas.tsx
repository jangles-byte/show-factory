import { useEffect } from "react";
import { ReactFlow, Background, Controls, useNodesState, useEdgesState } from "@xyflow/react";
import { useStore } from "./store";
import { SeasonNode, EpisodeNode } from "./nodes";

const nodeTypes = { season: SeasonNode, episode: EpisodeNode };

function epKey(ep: any, i: number) {
  return "ep" + String(ep.number ?? i + 1).padStart(2, "0");
}

export default function StoryCanvas() {
  const bible = useStore((s) => s.bible);
  const select = useStore((s) => s.select);
  const selected = useStore((s) => s.selected);
  const [nodes, setNodes, onNodesChange] = useNodesState([] as any);
  const [edges, setEdges, onEdgesChange] = useEdgesState([] as any);

  // rebuild graph when the show or its episode list changes
  const sig = JSON.stringify((bible?.episodes || []).map((e) => e.title));
  useEffect(() => {
    if (!bible) {
      setNodes([]);
      setEdges([]);
      return;
    }
    const eps = bible.episodes || [];
    const mid = Math.max(40, (eps.length * 130) / 2 - 50);
    const n: any[] = [{ id: "season", type: "season", position: { x: 40, y: mid }, data: { bible } }];
    const e: any[] = [];
    eps.forEach((ep, i) => {
      n.push({
        id: "ep-" + i,
        type: "episode",
        position: { x: 400, y: 40 + i * 130 },
        data: { ep, idx: i, status: bible._status?.[epKey(ep, i)] },
        selected: selected === "ep-" + i,
      });
      e.push({ id: "e-" + i, source: "season", target: "ep-" + i });
    });
    setNodes(n);
    setEdges(e);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bible?._slug, eps_len(bible), sig]);

  return (
    <div className="canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => select(node.id)}
        onPaneClick={() => select(null)}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#222630" gap={26} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function eps_len(b: any) {
  return (b?.episodes || []).length;
}
