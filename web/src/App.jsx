import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Services from './pages/Services';
import Team from './pages/Team';
import Availability from './pages/Availability';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="services" element={<Services />} />
        <Route path="equipe" element={<Team />} />
        <Route path="disponibilites" element={<Availability />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
