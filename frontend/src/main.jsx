import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import ErrorBoundary from "./components/ErrorBoundary.jsx";
import App from "./App.jsx";

// If you created these pages, keep these imports; otherwise temporarily comment them out.
// IMPORTANT: If any of these files don't exist, you'll get a blank screen.
// Make sure the files exist at these exact paths before importing.
import WorkoutVideosPage from "./pages/WorkoutVideosPage.jsx";
import WeekPlannerPage    from "./pages/WeekPlannerPage.jsx";
import GoalsPage          from "./pages/GoalsPage.jsx";

import "./styles.css";

const rootEl = document.getElementById("root");
if (!rootEl) {
  // If index.html doesn’t have <div id="root"></div>, React can’t mount.
  throw new Error("Root element #root not found in index.html");
}

createRoot(rootEl).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/workout-videos" element={<WorkoutVideosPage />} />
          <Route path="/plan-week" element={<WeekPlannerPage />} />
          <Route path="/goals" element={<GoalsPage />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
