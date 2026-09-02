import { Routes, Route, Navigate } from "react-router-dom";

import Dashboard from "./pages/dashboard/dashboard";
import Projects from "./pages/projects/projects";
import NewProject from "./pages/new-project/NewProject";
import NewProjectChat from "./pages/new-project/NewProjectChat";
import NewProjectForm from "./pages/new-project/NewProjectForm";
import ProjectDetail from "./pages/project-detail/ProjectDetail";

function AppRoutes() {
  return (
    <Routes>

      {/* Default */}
      <Route
        path="/"
        element={
          <Navigate
            to="/app/procurement-ai-assistant/dashboard"
            replace
          />
        }
      />

      {/* Dashboard */}
      <Route
        path="/dashboard"
        element={<Dashboard />}
      />

      {/* Projects */}
      <Route
        path="/projects"
        element={<Projects />}
      />

      <Route
        path="/projects/new"
        element={<NewProject />}
      />

      <Route
        path="/projects/new/chat"
        element={<NewProjectChat />}
      />

      <Route
        path="/projects/new/form"
        element={<NewProjectForm />}
      />

      {/* Project detail */}
      <Route
        path="/projects/:projectId"
        element={<ProjectDetail />}
      />

    </Routes>
  );
}

export default AppRoutes;
