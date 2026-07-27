import type { LogEntry } from "../../types";

interface Props {
  entry: LogEntry;
}

export default function ControllerPanel({ entry }: Props) {
  return (
    <div className="bg-white border rounded-lg p-3 text-sm">
      <div className="font-medium text-indigo-700 mb-1">Controller</div>
      <div className="space-y-1 text-gray-600">
        <div><span className="font-medium">Fn:</span> {entry.fn}</div>
        <div><span className="font-medium">Block:</span> {entry.block}</div>
        <div><span className="font-medium">Event:</span> {entry.event}</div>
        <div><span className="font-medium">Result:</span> {entry.result}</div>
        {entry.slice_id && <div><span className="font-medium">Slice:</span> {entry.slice_id}</div>}
      </div>
    </div>
  );
}

