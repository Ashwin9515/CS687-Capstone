// frontend/src/components/WorkoutVideos.jsx
import { useEffect, useState } from "react";

// Try to import API helpers; if missing, stub them so UI still works.
let getVideos = async () => [];
let saveVideo = async () => ({});
let deleteVideo = async () => ({ ok: true });
try {
  const api = await import("../api");
  getVideos   = api.getVideos   ?? getVideos;
  saveVideo   = api.saveVideo   ?? saveVideo;
  deleteVideo = api.deleteVideo ?? deleteVideo;
} catch { /* ok: fallback stubs */ }

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

const SAMPLE = [
  { id: "sample-1", title: "10-Minute Morning Mobility", url: "https://www.youtube.com/watch?v=Z4ziWoIo6lM", tags: ["mobility","stretch"] },
  { id: "sample-2", title: "20-Minute Full Body HIIT",   url: "https://www.youtube.com/watch?v=ml6cT4AZdqI", tags: ["hiit","cardio"] },
  { id: "sample-3", title: "15-Minute Core Strength",     url: "https://www.youtube.com/watch?v=1919eTCoESo", tags: ["core","strength"] },
];

export default function WorkoutVideos() {
  const [videos, setVideos] = useState([]);
  const [title, setTitle]   = useState("");
  const [url, setUrl]       = useState("");
  const [tags, setTags]     = useState("");
  const [editId, setEditId] = useState(null);
  const [err, setErr]       = useState("");

  useEffect(() => {
    (async () => {
      try {
        setErr("");
        const v = await getVideos();
        // If backend not ready, fall back to samples
        setVideos(Array.isArray(v) && v.length ? v : SAMPLE);
      } catch (e) {
        console.error(e);
        setErr("Using sample videos (backend not reachable)");
        setVideos(SAMPLE);
      }
    })();
  }, []);

  const load = async () => {
    try {
      const v = await getVideos();
      setVideos(Array.isArray(v) && v.length ? v : SAMPLE);
    } catch {
      setVideos(SAMPLE);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !url.trim()) return;
    try {
      const payload = {
        id: editId || undefined,
        title: title.trim(),
        url: url.trim(),
        tags: tags ? tags.split(",").map(t => t.trim()).filter(Boolean) : [],
      };
      await saveVideo(payload);
      setTitle(""); setUrl(""); setTags(""); setEditId(null);
      await load();
    } catch (e) {
      console.error(e);
      setErr("Failed to save video");
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteVideo(id);
      await load();
    } catch (e) {
      console.error(e);
      setErr("Failed to delete");
    }
  };

  const handleEdit = (v) => {
    setEditId(v.id);
    setTitle(v.title || "");
    setUrl(v.url || "");
    setTags((v.tags || []).join(", "));
  };

  return (
    <div className="card">
      <h3>Workout Videos</h3>
      {err && <div className="card error" style={{marginBottom: '.5rem'}}>{err}</div>}

      {/* Add / Update Form */}
      <form onSubmit={handleSubmit} className="row" style={{ gap: '.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type="text" placeholder="Title (e.g., 10-min Mobility)"
          value={title} onChange={(e)=>setTitle(e.target.value)}
          style={{ padding: '.5rem .6rem', border: '1px solid #e2e8f0', borderRadius: '10px', minWidth: '220px' }}
        />
        <input
          type="text" placeholder="YouTube/MP4 URL"
          value={url} onChange={(e)=>setUrl(e.target.value)}
          style={{ padding: '.5rem .6rem', border: '1px solid #e2e8f0', borderRadius: '10px', minWidth: '260px' }}
        />
        <input
          type="text" placeholder="tags (comma separated)"
          value={tags} onChange={(e)=>setTags(e.target.value)}
          style={{ padding: '.5rem .6rem', border: '1px solid #e2e8f0', borderRadius: '10px', minWidth: '200px' }}
        />
        <button className="btn" type="submit">{editId ? "Update" : "Add Video"}</button>
        {editId && (
          <button type="button" className="btn subtle" onClick={()=>{ setEditId(null); setTitle(""); setUrl(""); setTags(""); }}>
            Cancel Edit
          </button>
        )}
      </form>

      {/* Grid */}
      <div className="grid" style={{ marginTop: '.75rem', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem' }}>
        {videos.map(v => {
          const embedUrl = normalizeYoutube(v.url);
          const isYouTube = embedUrl.includes("youtube.com/embed/");
          return (
            <div key={v.id} className="card" style={{ overflow: 'hidden' }}>
              <div style={{ position: 'relative', paddingTop: '56.25%' }}>
                {isYouTube ? (
                  <iframe
                    src={embedUrl}
                    title={v.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    style={{ position:'absolute', inset:0, width:'100%', height:'100%', border:0 }}
                  />
                ) : (
                  <video
                    controls
                    src={v.url}
                    style={{ position:'absolute', inset:0, width:'100%', height:'100%', background:'#000' }}
                  />
                )}
              </div>
              <div style={{ marginTop: '.5rem' }}>
                <strong>{v.title}</strong>
                {!!(v.tags && v.tags.length) && (
                  <div className="muted" style={{ marginTop: '.25rem' }}>
                    {v.tags.map((t,i)=><span key={i} style={{ marginRight: '.4rem' }}>#{t}</span>)}
                  </div>
                )}
              </div>
              <div className="row" style={{ marginTop: '.5rem', gap: '.5rem' }}>
                <button className="btn subtle" onClick={()=>handleEdit(v)}>Edit</button>
                <button className="btn" onClick={()=>handleDelete(v.id)}>Delete</button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  );
}
