import Navbar from "./components/Navbar/Navbar";
import { Routes } from "react-router-dom";

import AppRoutes from "./routes";

import "./app.css";

function ProcurementApp() {
  return (
    <div className="procurement-app">

      <Navbar />

      <main className="procurement-main">
        <AppRoutes />
      </main>

    </div>
  );
}

export default ProcurementApp;