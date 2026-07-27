interface Props {
  escalation: { reason: string; details: string };
  onClose: () => void;
}

export default function EscalationModal({ escalation, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h2 className="text-lg font-bold text-red-700 mb-2">Escalation</h2>
        <p className="font-medium text-gray-900">{escalation.reason}</p>
        <p className="text-sm text-gray-600 mt-1">{escalation.details}</p>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Acknowledge
          </button>
        </div>
      </div>
    </div>
  );
}

