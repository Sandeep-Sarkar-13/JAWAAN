import { Route, Routes } from "react-router-dom";
import SosList from "./components/SosList";
import SosForm from "./components/SosForm";

function App() {
  return (
  
      <Routes>
        <Route path="/sos-list" element={<SosList />} />
        <Route path="/" element={<SosForm />} />
      </Routes>
  
  );
}

export default App;
