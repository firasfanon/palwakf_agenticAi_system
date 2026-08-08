import { Route, Routes } from "react-router-dom";

export function ProjectDashboard() {
  return <main>Dashboard</main>;
}

const ReviewPanel = () => <section>Review</section>;

export function App() {
  return (
    <Routes>
      <Route path="/projects" element={<ProjectDashboard />} />
      <Route path="/projects/:projectId/review" element={<ReviewPanel />} />
    </Routes>
  );
}
