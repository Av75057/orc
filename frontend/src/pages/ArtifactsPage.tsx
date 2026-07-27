import { useEffect, useState } from "react";
import { getArtifacts, getArtifactContent, saveArtifact, createArtifact } from "../api/graceApi";
import type { ArtifactFile } from "../api/graceApi";

export default function ArtifactsPage() {
  const [files, setFiles] = useState<ArtifactFile[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [showNewFile, setShowNewFile] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadFiles = () => { getArtifacts().then((data) => setFiles(data.files)).catch(() => {}); };
  useEffect(() => { loadFiles(); }, []);

  const handleSelect = async (file: ArtifactFile) => {
    if (dirty && !confirm("Discard unsaved changes?")) return;
    setSelected(file.path);
    setDirty(false);
    setMsg("");
    try {
      const text = await getArtifactContent(file.path);
      setContent(text);
    } catch {
      setContent("// Error loading file");
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    setMsg("");
    try {
      await saveArtifact(selected, content);
      setDirty(false);
      setMsg("Saved");
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    const name = newFileName.trim();
    if (!name) return;
    setCreating(true);
    setMsg("");
    try {
      await createArtifact(name);
      setNewFileName("");
      setShowNewFile(false);
      await loadFiles();
      setSelected(`docs/${name}`);
      setContent("");
      setDirty(false);
      setMsg("Created");
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="flex gap-6 h-[calc(100vh-4rem)]">
      <aside className="w-64 border-r overflow-y-auto shrink-0 p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-sm">Artifacts (docs/)</h2>
          <button onClick={() => setShowNewFile(!showNewFile)} className="text-xs px-2 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700">+ New</button>
        </div>
        {showNewFile && (
          <div className="mb-3 flex gap-1">
            <input type="text" value={newFileName} onChange={(e) => setNewFileName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder="name.xml or name.md"
              className="flex-1 text-xs border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-300" autoFocus />
            <button onClick={handleCreate} disabled={creating || !newFileName.trim()}
              className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50">
              {creating ? "..." : "OK"}
            </button>
          </div>
        )}
        {files.length === 0 && <p className="text-gray-400 text-sm">No files found.</p>}
        <ul className="space-y-1">
          {files.map((f) => (
            <li key={f.path}>
              <button onClick={() => handleSelect(f)}
                className={`w-full text-left text-sm px-2 py-1 rounded hover:bg-indigo-50 ${selected === f.path ? "bg-indigo-100 font-medium text-indigo-700" : "text-gray-700"}`}>
                {f.name}
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <main className="flex-1 flex flex-col p-4">
        {selected ? (
          <>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-gray-500 font-mono">{selected}</p>
              <div className="flex items-center gap-3">
                {msg && <span className={`text-xs ${msg.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>{msg}</span>}
                <button onClick={handleSave} disabled={saving || !dirty}
                  className={`px-4 py-1.5 text-sm rounded ${dirty ? "bg-indigo-600 text-white hover:bg-indigo-700" : "bg-gray-100 text-gray-400 cursor-not-allowed"}`}>
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>
            <textarea value={content} onChange={(e) => { setContent(e.target.value); setDirty(true); }}
              className="flex-1 font-mono text-sm border rounded p-3 resize-none focus:outline-none focus:ring-1 focus:ring-indigo-300" />
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">Select a file to edit</div>
        )}
      </main>
    </div>
  );
}

