import { useEffect, useState } from "react";
import { getEvidenceTree, getEvidenceFile } from "../api/graceApi";
import type { TreeNode } from "../types";

export default function EvidencePage() {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  useEffect(() => { getEvidenceTree().then(setTree).catch(() => {}); }, []);

  const handleClick = async (node: TreeNode, path: string) => {
    if (node.type === "file") {
      setSelectedPath(path);
      try {
        const text = await getEvidenceFile(path);
        setContent(text);
      } catch { setContent("Error loading file"); }
    }
  };

  const renderTree = (node: TreeNode, basePath: string): JSX.Element => {
    const fullPath = basePath ? `${basePath}/${node.name}` : node.name;
    return (
      <li key={fullPath}>
        {node.type === "directory" ? (
          <details open>
            <summary className="cursor-pointer text-sm font-medium text-gray-700">{node.name}/</summary>
            <ul className="ml-4 space-y-1 mt-1">
              {node.children?.map((c) => renderTree(c, fullPath))}
            </ul>
          </details>
        ) : (
          <button onClick={() => handleClick(node, fullPath)}
            className={`text-sm w-full text-left px-2 py-0.5 rounded hover:bg-indigo-50 ${selectedPath === fullPath ? "bg-indigo-100 text-indigo-700" : "text-gray-600"}`}>
            {node.name}
          </button>
        )}
      </li>
    );
  };

  return (
    <div className="flex gap-6 h-[calc(100vh-4rem)]">
      <aside className="w-64 border-r overflow-y-auto shrink-0 p-4">
        <h2 className="font-semibold text-sm mb-3">Evidence</h2>
        {tree && <ul>{renderTree(tree, "")}</ul>}
      </aside>
      <main className="flex-1 flex flex-col p-4">
        {content ? (
          <pre className="flex-1 font-mono text-sm bg-gray-50 border rounded p-4 overflow-auto whitespace-pre-wrap">{content}</pre>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">Select a file to view</div>
        )}
      </main>
    </div>
  );
}

