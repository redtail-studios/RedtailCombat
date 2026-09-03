import { Radar, Brain, FlaskConical, Hammer, Rocket, RefreshCw } from "lucide-react";

export const STAGES = [
  { n: "01", name: "sense", Icon: Radar, owner: "agents", input: "forums · stores · reviews · creator content", output: "raw behavioral signal", lore: "Agents crawl the noise of the internet around the clock and tag what players actually complain about, praise, and replay." },
  { n: "02", name: "synthesize", Icon: Brain, owner: "agents", input: "signal clusters", output: "ranked game concepts", lore: "Clusters of signal get compressed into concepts and ranked by demand, feasibility, and how bored the market is." },
  { n: "03", name: "simulate", Icon: FlaskConical, owner: "agents", input: "concepts", output: "prototypes + AI-vs-AI balance data", lore: "Top concepts become playable prototypes. Agents play them against each other until the fun (or the lack of it) is measurable." },
  { n: "04", name: "build", Icon: Hammer, owner: "humans", input: "strongest concept", output: "a shipped mobile title", lore: "The one stage humans own end to end. The PM-led team takes the winner and ships production code." },
  { n: "05", name: "launch", Icon: Rocket, owner: "agents + humans", input: "the title", output: "live-ops · marketing · updates", lore: "Go live. Agents handle live-ops telemetry and marketing tests; humans make the calls that need taste." },
  { n: "06", name: "learn", Icon: RefreshCw, owner: "agents", input: "performance data", output: "a retrained engine for the next pick", lore: "Every launch retrains the engine. The next pick starts smarter than the last one did." },
];