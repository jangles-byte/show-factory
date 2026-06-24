import { useStore, type LeftTab } from "./store";
import ShowsPanel from "./ShowsPanel";
import CharactersPanel from "./CharactersPanel";
import StylesPanel from "./StylesPanel";
import RendersPanel from "./RendersPanel";
import PlaygroundPanel from "./PlaygroundPanel";

const TABS: { id: LeftTab; label: string; icon: string }[] = [
  { id: "shows", label: "SHOWS", icon: "▤" },
  { id: "characters", label: "CAST", icon: "☺" },
  { id: "styles", label: "STYLES", icon: "✦" },
  { id: "playground", label: "IMAGE", icon: "❖" },
  { id: "renders", label: "RENDERS", icon: "▶" },
];

export default function Sidebar() {
  const { leftTab, setLeftTab } = useStore();

  return (
    <nav className="rail">
      <div className="brand">
        SHOW&nbsp;FACTORY
        <small>PRODUCTION SUITE</small>
      </div>

      <div className="tabbar">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={"tab" + (leftTab === t.id ? " active" : "")}
            onClick={() => setLeftTab(t.id)}
            title={t.label}
          >
            <span className="ti">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      <div className="panelwrap">
        {leftTab === "shows" && <ShowsPanel />}
        {leftTab === "characters" && <CharactersPanel />}
        {leftTab === "styles" && <StylesPanel />}
        {leftTab === "playground" && <PlaygroundPanel />}
        {leftTab === "renders" && <RendersPanel />}
      </div>
    </nav>
  );
}
