import { useRef, useState } from "react";
import { useStore } from "./store";
import { chatStream } from "./api";

const SYSTEM =
  "You are a sharp, friendly TV showrunner helping develop a show. Be concise and conversational, ask focused questions, suggest concretely. Any genre — never assume one.";

type Msg = { role: "user" | "assistant"; content: string };

export default function WritersRoom() {
  const model = useStore((s) => s.model);
  const bible = useStore((s) => s.bible);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  const context = bible
    ? `Current show: ${bible.title} — ${bible.genre} (${bible.tone}). Logline: ${bible.logline}. Episodes: ${(bible.episodes || []).map((e) => e.title).join(", ")}.`
    : "No show open yet.";

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    const next = [...msgs, { role: "user", content: text } as Msg];
    setMsgs([...next, { role: "assistant", content: "" }]);
    setBusy(true);
    const history = [{ role: "system", content: SYSTEM + "\n" + context }, ...next];
    let acc = "";
    try {
      for await (const tok of chatStream(history, model)) {
        acc += tok;
        setMsgs([...next, { role: "assistant", content: acc }]);
        scroller.current?.scrollTo(0, 1e9);
      }
    } catch (e: any) {
      setMsgs([...next, { role: "assistant", content: "⚠ " + e.message }]);
    }
    setBusy(false);
  }

  return (
    <div className="writers">
      <div className="ihead">[ WRITERS' ROOM ]</div>
      <div className="chat" ref={scroller}>
        {msgs.length === 0 && <div className="hint">Ask the showrunner about the open show, or brainstorm an episode.</div>}
        {msgs.map((m, i) => (
          <div className={"cmsg " + m.role} key={i}>
            <div className="who">{m.role === "user" ? "YOU" : "SHOWRUNNER"}</div>
            <div className="bub">{m.content || "…"}</div>
          </div>
        ))}
      </div>
      <div className="composer">
        <textarea
          rows={1}
          value={input}
          placeholder="› talk to the showrunner"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="go" disabled={busy} onClick={send}>
          SEND
        </button>
      </div>
    </div>
  );
}
