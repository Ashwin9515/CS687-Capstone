import { useEffect, useState } from "react";
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

export default function WorkoutVideosPage() {
  const [videos, setVideos] = useState([]);

  useEffect(() => {
    (async () => {
      const list = await getVideos();
      setVideos(Array.isArray(list) ? list : []);
    })();
  }, []);

  return (
    <div className="container">
      <header className="hero">
        <h1>Workout <span className="accent">Videos</span></h1>
        <p>Browse your exercise video library</p>
      </header>

      <section className="grid">
        {videos.map((v) => {
          const embed = normalizeYoutube(v.url);
          return (
            <div className="card" key={v.id}>
              <h3>{v.title}</h3>
              <div className="video-wrapper">
                {embed.includes("youtube.com/embed/") ? (
                  <iframe
                    src={embed}
                    title={v.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    className="w-full h-64 border-0 rounded-lg"
                  />
                ) : (
                  <video src={v.url} controls className="w-full h-64 rounded-lg" />
                )}
              </div>
              <div className="tags">
                {(v.tags || []).map((t, i) => (
                  <span key={i} className="tag">#{t}</span>
                ))}
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}
