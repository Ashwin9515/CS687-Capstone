import { useEffect, useMemo, useState } from "react";
import { getVideos } from "../api";

function normalizeYoutube(url) {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtube.com")) {
      const v = u.searchParams.get("v");
      if (v) return `https://www.youtube.com/embed/${v}`;
      if (u.pathname.startsWith("/embed/")) return url;
      if (u.pathname.startsWith("/shorts/")) {
        const id = u.pathname.split("/")[2];
        if (id) return `https://www.youtube.com/embed/${id}`;
      }
    }
    if (u.hostname === "youtu.be") {
      const id = u.pathname.slice(1);
      if (id) return `https://www.youtube.com/embed/${id}`;
    }
  } catch {}
  return url;
}

export default function VideoGalleryModal({ open, onClose, startAtId }) {
  const [videos, setVideos] = useState([]);
  const [idx, setIdx] = useState(0);

  // load videos
  useEffect(() => {
    if (!open) return;
    (async () => {
      const list = await getVideos();
      setVideos(Array.isArray(list) ? list : []);
    })();
  }, [open]);

  // position to a specific video if provided
  useEffect(() => {
    if (!open || !startAtId || videos.length === 0) return;
    const i = videos.findIndex(v => v.id === startAtId);
    if (i >= 0) setIdx(i);
  }, [open, startAtId, videos]);

  const current = videos[idx] || null;
  const embedUrl = useMemo(
    () => (current ? normalizeYoutube(current.url) : ""),
    [current]
  );

  const next = () => setIdx(i => (videos.length ? (i + 1) % videos.length : 0));
  const prev = () => setIdx(i => (videos.length ? (i - 1 + videos.length) % videos.length : 0));

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[999] bg-black/60 backdrop-blur-sm flex">
      <div className="m-auto w-[min(1100px,95vw)] h-[min(80vh,800px)] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <div className="font-semibold">
            Workout Videos {current ? `— ${current.title}` : ""}
          </div>
          <button className="btn" onClick={onClose}>Close ✕</button>
        </div>

        {/* Player + Controls */}
        <div className="flex-1 grid md:grid-cols-[72px_1fr_72px]">
          {/* Prev */}
          <div className="hidden md:flex items-center justify-center">
            <button className="btn" onClick={prev} aria-label="Previous video">‹</button>
          </div>

          {/* Player */}
          <div className="p-3 flex flex-col">
            <div className="relative w-full pb-[56.25%] bg-black/80 rounded-xl overflow-hidden">
              {current && (embedUrl.includes("youtube.com/embed/") ? (
                <iframe
                  key={current.id}
                  src={embedUrl}
                  title={current.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  className="absolute inset-0 w-full h-full border-0"
                />
              ) : (
                <video key={current?.id} src={current?.url} controls className="absolute inset-0 w-full h-full"/>
              ))}
            </div>

            {/* Title + tags */}
            {current && (
              <div className="mt-3">
                <div className="text-lg font-semibold">{current.title}</div>
                <div className="text-sm text-gray-500 mt-1">
                  {(current.tags || []).map((t, i) => (
                    <span key={i} className="mr-3">#{t}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Next */}
          <div className="hidden md:flex items-center justify-center">
            <button className="btn" onClick={next} aria-label="Next video">›</button>
          </div>
        </div>

        {/* Thumbnails rail */}
        <div className="px-3 py-2 border-t overflow-x-auto flex gap-2">
          {videos.map((v, i) => {
            const thumb = normalizeYoutube(v.url)
              .match(/embed\/([A-Za-z0-9_-]+)/)?.[1];
            const thumbUrl = thumb
              ? `https://img.youtube.com/vi/${thumb}/mqdefault.jpg`
              : null;
            const active = i === idx;
            return (
              <button
                key={v.id}
                onClick={() => setIdx(i)}
                className={`shrink-0 rounded-lg border ${active ? "ring-2 ring-sky-500" : "border-gray-200"}`}
                title={v.title}
                style={{ width: 160 }}
              >
                <div className="relative w-full pb-[56.25%] bg-gray-100 rounded-t-lg overflow-hidden">
                  {thumbUrl ? (
                    <img src={thumbUrl} alt={v.title} className="absolute inset-0 w-full h-full object-cover" />
                  ) : (
                    <div className="absolute inset-0 grid place-items-center text-xs text-gray-500">No preview</div>
                  )}
                </div>
                <div className="p-2 text-left text-xs truncate">{v.title}</div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
