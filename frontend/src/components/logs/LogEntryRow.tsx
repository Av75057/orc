import type { LogEntry } from "../../types";
import { RESULT_COLORS } from "../../types";

interface Props {
  entry: LogEntry;
  onClick: () => void;
  selected: boolean;
}

export default function LogEntryRow({ entry, onClick, selected }: Props) {
  const color = RESULT_COLORS[entry.result] || "bg-gray-100 text-gray-600";
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 border-b text-sm flex items-center gap-2 hover:bg-gray-50 ${
        selected ? "bg-indigo-50" : ""
      }`}
    >
      <span className="text-xs text-gray-400 w-16 shrink-0">{entry.timestamp?.slice(11, 19) || ""}</span>
      <span className="w-20 shrink-0 font-medium">{entry.module}</span>
      <span className="truncate flex-1">{entry.event}</span>
      <span className={`text-xs px-1.5 py-0.5 rounded ${color}`}>{entry.result}</span>
    </button>
  );
}

