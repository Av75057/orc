import { useParams } from "react-router-dom";

export default function WaveDetailPage() {
  const { phaseId, waveId } = useParams();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Wave: {waveId}</h1>
      <p className="text-gray-600">Phase: {phaseId}</p>
    </div>
  );
}

