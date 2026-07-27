import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import ArtifactsPage from "./pages/ArtifactsPage";
import EvidencePage from "./pages/EvidencePage";
import LogsPage from "./pages/LogsPage";
import WaveDetailPage from "./pages/WaveDetailPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/artifacts" element={<ArtifactsPage />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/wave/:phaseId/:waveId" element={<WaveDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
