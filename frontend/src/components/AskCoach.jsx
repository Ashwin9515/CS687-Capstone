// frontend/src/components/AskCoach.jsx
import { useState } from "react";
import { askCoach } from "../api";

export default function AskCoach() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [ans, setAns] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const handleAsk = async () => {
    if (!q.trim()) return;
    setLoading(true);
    setErr("");
    setAns("");
    try {
      const { reply } = await askCoach(q);
      setAns(reply);
    } catch (e) {
      setErr(e?.message || "Failed to ask coach");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Quick Action button */}
      <button
        className="btn qa ask"
        onClick={() => setOpen(true)}
      >
        Ask AI Coach
        <small>Get personalized advice</small>
      </button>

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-xl rounded-2xl bg-white p-5 shadow-xl">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold">Ask AI Coach</h2>
              <button className="text-gray-500" onClick={() => setOpen(false)}>✕</button>
            </div>

            <textarea
              className="w-full border rounded-lg p-3 min-h-[110px] mt-3 outline-none"
              placeholder="e.g., I'm sore today and only slept 6 hours. What should I do?"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />

            <div className="mt-3 flex gap-2">
              <button
                className="px-4 py-2 rounded-lg bg-gray-200"
                onClick={() => setOpen(false)}
              >
                Close
              </button>
              <button
                className="px-4 py-2 rounded-lg bg-sky-600 text-white disabled:opacity-60"
                onClick={handleAsk}
                disabled={loading}
              >
                {loading ? "Asking..." : "Send"}
              </button>
            </div>

            {err && (
              <div className="mt-3 rounded-lg bg-rose-50 text-rose-700 p-3">
                Error: {err}
              </div>
            )}

            {ans && (
              <div className="mt-4 rounded-lg bg-emerald-50 text-emerald-900 p-3 whitespace-pre-wrap">
                {ans}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
