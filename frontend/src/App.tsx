import { useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Nav } from "@/components/Nav";
import { DashboardPage } from "@/pages/DashboardPage";
import { DecisionLogPage } from "@/pages/DecisionLogPage";
import { FlagReviewPage } from "@/pages/FlagReviewPage";
import { ReviewQueuePage } from "@/pages/ReviewQueuePage";
import { StudyDetailPage } from "@/pages/StudyDetailPage";

export default function App() {
  const [pendingCount, setPendingCount] = useState(0);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
        <Nav pendingCount={pendingCount} />
        <Routes>
          <Route path="/"                    element={<DashboardPage />} />
          <Route path="/studies/:studyId"    element={<StudyDetailPage />} />
          <Route path="/queue"               element={<ReviewQueuePage onPendingCountChange={setPendingCount} />} />
          <Route path="/log"                 element={<DecisionLogPage />} />
          <Route path="/review/:datasetId"   element={<FlagReviewPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
