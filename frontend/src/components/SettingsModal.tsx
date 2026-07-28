import { useState, useEffect } from "react";

const LS_OPENAI_KEY = "grace_openai_api_key";
const LS_GITHUB_TOKEN = "grace_github_token";
const LS_LLM_MODEL = "grace_llm_model";
const LS_LLM_API_URL = "grace_llm_api_url";
const LS_WORKSPACE = "grace_workspace";

interface Props {
  onClose: () => void;
}

export default function SettingsModal({ onClose }: Props) {
  const [openaiKey, setOpenaiKey] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [llmModel, setLlmModel] = useState("gpt-4o-mini");
  const [llmApiUrl, setLlmApiUrl] = useState("https://api.openai.com/v1/chat/completions");
  const [workspace, setWorkspace] = useState("");

  useEffect(() => {
    setOpenaiKey(localStorage.getItem(LS_OPENAI_KEY) || "");
    setGithubToken(localStorage.getItem(LS_GITHUB_TOKEN) || "");
    setLlmModel(localStorage.getItem(LS_LLM_MODEL) || "deepseek-chat");
    setLlmApiUrl(localStorage.getItem(LS_LLM_API_URL) || "https://api.deepseek.com/chat/completions");
    setWorkspace(localStorage.getItem(LS_WORKSPACE) || "");
  }, []);

  const handleSave = () => {
    if (openaiKey) localStorage.setItem(LS_OPENAI_KEY, openaiKey);
    else localStorage.removeItem(LS_OPENAI_KEY);
    if (githubToken) localStorage.setItem(LS_GITHUB_TOKEN, githubToken);
    else localStorage.removeItem(LS_GITHUB_TOKEN);
    if (llmModel) localStorage.setItem(LS_LLM_MODEL, llmModel);
    else localStorage.removeItem(LS_LLM_MODEL);
    if (llmApiUrl) localStorage.setItem(LS_LLM_API_URL, llmApiUrl);
    else localStorage.removeItem(LS_LLM_API_URL);
    if (workspace) localStorage.setItem(LS_WORKSPACE, workspace);
    else localStorage.removeItem(LS_WORKSPACE);
    onClose();
  };

  const handleClear = () => {
    localStorage.removeItem(LS_OPENAI_KEY);
    localStorage.removeItem(LS_GITHUB_TOKEN);
    localStorage.removeItem(LS_LLM_MODEL);
    localStorage.removeItem(LS_LLM_API_URL);
    localStorage.removeItem(LS_WORKSPACE);
    setOpenaiKey("");
    setGithubToken("");
    setLlmModel("deepseek-chat");
    setLlmApiUrl("https://api.deepseek.com/chat/completions");
    setWorkspace("");
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h2 className="text-lg font-bold mb-4">Settings</h2>

        <label className="block text-sm font-medium text-gray-700 mb-1">LLM API Key</label>
        <input type="password" value={openaiKey} onChange={(e) => setOpenaiKey(e.target.value)}
          placeholder="sk-..." className="w-full border rounded px-3 py-2 text-sm mb-4" />

        <label className="block text-sm font-medium text-gray-700 mb-1">LLM Model</label>
        <input type="text" value={llmModel} onChange={(e) => setLlmModel(e.target.value)}
          placeholder="gpt-4o-mini" className="w-full border rounded px-3 py-2 text-sm mb-4" />

        <label className="block text-sm font-medium text-gray-700 mb-1">LLM API URL</label>
        <input type="text" value={llmApiUrl} onChange={(e) => setLlmApiUrl(e.target.value)}
          placeholder="https://api.openai.com/v1/chat/completions" className="w-full border rounded px-3 py-2 text-sm mb-4" />

        <label className="block text-sm font-medium text-gray-700 mb-1">Target Workspace Path</label>
        <input type="text" value={workspace} onChange={(e) => setWorkspace(e.target.value)}
          placeholder="/root/my_project" className="w-full border rounded px-3 py-2 text-sm mb-4" />

        <label className="block text-sm font-medium text-gray-700 mb-1">GitHub Token</label>
        <input type="password" value={githubToken} onChange={(e) => setGithubToken(e.target.value)}
          placeholder="ghp_..." className="w-full border rounded px-3 py-2 text-sm mb-4" />

        <div className="flex gap-3 justify-end">
          <button onClick={handleClear} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Clear</button>
          <button onClick={onClose} className="px-4 py-2 text-sm bg-gray-100 rounded hover:bg-gray-200">Cancel</button>
          <button onClick={handleSave} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700">Save & Close</button>
        </div>
      </div>
    </div>
  );
}



