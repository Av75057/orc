import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHealth, getState, getArtifacts, runOrchestrator, resetState } from "../api/graceApi";
import type { HealthStatus, GraceState, ArtifactList } from "../api/graceApi";
import EscalationModal from "../components/EscalationModal";
import SettingsModal from "../components/SettingsModal";

const LS_OPENAI_KEY = "grace_openai_api_key";
const LS_GITHUB_TOKEN = "grace_github_token";
const LS_LLM_MODEL = "grace_llm_model";
const LS_LLM_API_URL = "grace_llm_api_url";
const LS_WORKSPACE = "grace_workspace";

export default function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [state, setState] = useState<GraceState | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showEscalation, setShowEscalation] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

  const loadData = () => {
    Promise.all([
      getHealth().catch(() => null),
      getState().catch(() => null),
      getArtifacts().catch(() => null),
    ])
      .then(([h, s, a]) => {
        if (h) setHealth(h);
        if (s) setState(s);
        if (a) setArtifacts(a);
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => { loadData(); }, []);

  const handleReset = async () => {
    if (!confirm("Are you sure you want to reset the state?")) return;
    try {
      await resetState();
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setRunResult(null);
    setError(null);
    try {
      const openaiKey = localStorage.getItem(LS_OPENAI_KEY) || undefined;
      const githubToken = localStorage.getItem(LS_GITHUB_TOKEN) || undefined;
      const llmModel = localStorage.getItem(LS_LLM_MODEL) || undefined;
      const llmApiUrl = localStorage.getItem(LS_LLM_API_URL) || undefined;
      const workspace = localStorage.getItem(LS_WORKSPACE) || undefined;
      const result = await runOrchestrator({
        openai_api_key: openaiKey,
        github_token: githubToken,
        llm_model: llmModel,
        llm_api_url: llmApiUrl,
        workspace: workspace,
      });
      setRunResult(`Exit code: ${result.exit_code}`);
      if (result.exit_code !== 0 && result.stderr) {
        setRunResult(`Exit code: ${result.exit_code}\n${result.stderr}`);
      }
      loadData();
    } catch (e: any) {
      setRunResult(`Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {state?.escalation && showEscalation && (
        <EscalationModal escalation={state.escalation} onClose={() => setShowEscalation(false)} />
      )}
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex gap-2">
          <button onClick={handleRun} disabled={running}
            className="px-4 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {running ? "Running..." : "Run Orchestrator"}
          </button>
          <button
            onClick={handleReset}
            className="px-3 py-1.5 text-sm bg-red-500 text-white rounded hover:bg-red-600"
          >
            Reset State
          </button>
          <button onClick={() => setShowSettings(true)}
            className="px-3 py-1.5 text-sm bg-gray-100 border rounded hover:bg-gray-200">
            Settings
          </button>
        </div>
      </div>

      {runResult && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 rounded p-3 font-mono text-xs whitespace-pre-wrap">{runResult}</div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded p-4">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="Status" value={health?.status ?? "N/A"} />
        <StatCard title="Waves Completed" value={String(state?.completed_waves.length ?? 0)} />
        <StatCard title="Artifacts" value={String(artifacts?.files.length ?? 0)} />
      </div>

      {state?.github_mode && (
        <div className="bg-blue-50 border border-blue-200 rounded p-4">
          <p className="font-medium text-blue-800">GitHub Mode Active</p>
          {state.pr_url && (
            <a href={state.pr_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm">
              PR #{state.pr_number}
            </a>
          )}
          {state.merged && <span className="ml-3 inline-block bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded">Merged</span>}
        </div>
      )}

      {state && state.completed_waves.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-2">Completed Waves</h2>
          <ul className="space-y-1">
            {state.completed_waves.map((w) => (
              <li key={w}>
                <Link to={`/wave/${w.split("-")[0] || "PHASE-1"}/${w}`} className="text-indigo-600 hover:text-indigo-800 hover:underline">{w}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {state?.escalation && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded p-4">
          <p className="font-medium">Escalation: {state.escalation.reason}</p>
          {state.escalation.details && <p className="text-sm mt-1">{state.escalation.details}</p>}
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}


