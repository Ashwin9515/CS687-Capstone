import axios from "axios";

// Use env if present; fallback to localhost for dev
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:5000",
});

// Simple demo auth header
API.interceptors.request.use((cfg) => {
  cfg.headers["X-User-Id"] = "U123";
  return cfg;
});

// -------- Auth / Me --------
export const login = (userId = "U123", name = "Demo User") =>
  API.post("/auth/login", { userId, name });

// -------- Daily plan + actions --------
export const getPlan      = () => API.get("/me/plan").then((r) => r.data);
export const startPlan    = () => API.post("/me/plan/start").then((r) => r.data);
export const completePlan = () => API.post("/me/plan/complete").then((r) => r.data);

// -------- Weekly plan --------
export const getWeekPlan        = () => API.get("/me/plan/week").then((r) => r.data);
export const regenerateWeekPlan = () => API.post("/me/plan/week/regenerate").then((r) => r.data);
export const startPlanOnDate    = (isoDate) => API.post(`/me/plan/${isoDate}/start`).then((r) => r.data);
export const completePlanOnDate = (isoDate) => API.post(`/me/plan/${isoDate}/complete`).then((r) => r.data);

// Back-compat aliases if your page still imports old names:
export const startOnDate    = startPlanOnDate;
export const completeOnDate = completePlanOnDate;

// -------- Metrics --------
export const ingest      = (metricType, value) => API.post("/me/metrics", { metricType, value });
export const listMetrics = () => API.get("/me/metrics").then((r) => r.data);
export const setSteps    = (value) => API.post("/me/metrics/steps", { value }).then((r) => r.data);

// -------- Recommendations / coach --------
export const getRecs   = () => API.get("/me/recommendations").then((r) => r.data);
export const makeNudge = () => API.post("/me/nudge").then((r) => r.data);
export const askCoach  = (message) => API.post("/coach/ask", { message }).then((r) => r.data);

// -------- Workout videos --------
export const getVideos   = () => API.get("/videos").then((r) => r.data);
export const saveVideo   = (payload) => API.post("/videos", payload).then((r) => r.data);
export const deleteVideo = (id) => API.post("/videos/delete", { id }).then((r) => r.data);

// -------- Goals --------
export const getGoals   = () => API.get("/me/goals").then((r) => r.data);
export const createGoal = (payload) => API.post("/me/goals", payload).then((r) => r.data);
export const updateGoal = (id, payload) => API.patch(`/me/goals/${id}`, payload).then((r) => r.data);
export const deleteGoal = (id) => API.delete(`/me/goals/${id}`).then((r) => r.data);

export default API;
