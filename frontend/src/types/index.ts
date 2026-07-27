export interface TreeNode {
  name: string;
  type: "file" | "directory" | "missing";
  size?: number;
  children?: TreeNode[];
}

export interface LogEntry {
  timestamp: string;
  module: string;
  fn: string;
  block: string;
  event: string;
  result: string;
  trace_id?: string;
  scenario_id?: string;
  slice_id?: string;
  [key: string]: unknown;
}

export const RESULT_COLORS: Record<string, string> = {
  ok: "bg-green-100 text-green-800",
  fail: "bg-red-100 text-red-800",
  retry: "bg-yellow-100 text-yellow-800",
  skip: "bg-gray-100 text-gray-600",
};

