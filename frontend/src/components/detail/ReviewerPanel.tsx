import type { LogEntry } from "../../types";

interface Props {
  entry: LogEntry;
}

export default function ReviewerPanel({ entry }: Props) {
  return (
    <div className="bg-white border rounded-lg p-3 text-sm">
      <div className="font-medium text-orange-700 mb-1">Reviewer</div>
      <div className="space-y-1 text-gray-600">
        <div><span className="font-medium">Fn:</span> {entry.fn}</div>
        <div><span className="font-medium">Block:</span> {entry.block}</div>
        <div><span className="font-medium">Event:</span> {entry.event}</div>
        <div><span className="font-medium">Result:</span> {entry.result}</div>
      </div>
    </div>
  );
}

