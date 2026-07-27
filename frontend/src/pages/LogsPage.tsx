import { useEffect, useState } from "react";
import { getEvidenceTree, getEvidenceFile, parseLogs } from "../api/graceApi";
import type { TreeNode, LogEntry } from "../types";

export default function LogsPage() {
  const [entries, setEntries] = useState<(LogEntry | { error: string; raw: string })[]>([]);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const loadLogs = async () => {
    setLoading(true);
    setNotice(null);
    try {
      const tree = await getEvidenceTree();
      const stdoutFiles = findStdoutFiles(tree);
      const allEntries: (LogEntry | { error: string; raw: string })[] = [];

      for (const path of stdoutFiles) {
        try {
          const text = await getEvidenceFile(path);
          allEntries.push(...parseLogs(text));
        } catch {
          allEntries.push({ error: "Failed to load", raw: path });
        }
      }

      setEntries(allEntries);
      if (allEntries.length === 0) {
        setNotice("No logs yet. Run the orchestrator to generate logs.");
      }
    } catch (e: any) {
      setNotice(e.message || "Failed to load logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadLogs(); }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Logs</h1>
        <button onClick={loadLogs} disabled={loading}
          className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {notice && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded p-4 text-sm">{notice}</div>
      )}

      {loading && entries.length === 0 && (
        <div className="text-gray-400 text-sm">Loading logs...</div>
      )}

      <div className="space-y-1">
        {entries.map((entry, i) => {
          const isError = "error" in entry;
          const err = entry as { error: string; raw: string };
          const log = entry as LogEntry;
          return (
            <div key={i}
              className={`text-xs font-mono p-2 rounded border ${
                isError
                  ? "bg-yellow-50 border-yellow-200 text-yellow-800"
                  : log.result === "fail"
                  ? "bg-red-50 border-red-200 text-red-800"
                  : "bg-white border-gray-100 text-gray-700"
              }`}>
              <span>
                {isError
                  ? `${err.error}: ${err.raw}`
                  : `${log.timestamp?.slice(11, 19) || ""} [${log.module}] ${log.fn}: ${log.event} \u2192 ${log.result}`}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function findStdoutFiles(node: TreeNode, prefix: string = ""): string[] {
  const nodeName = node.name === "evidence" ? "" : node.name;
  const fullPath = prefix ? `${prefix}/${nodeName}` : nodeName;
  if (node.type === "file" && nodeName === "worker_stdout.txt") {
    return [fullPath];
  }
  if (node.type === "directory" && node.children) {
    return node.children.flatMap((child) => findStdoutFiles(child, nodeName));
  }
  return [];
}

