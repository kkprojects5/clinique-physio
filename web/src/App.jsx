import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Services from './pages/Services';
import Team from './pages/Team';
import Availability from './pages/Availability';
import NotFound from './pages/NotFound';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import VerifyEmail from './pages/VerifyEmail';
import Login from './pages/Login';
import Register from './pages/Register';
import Book from './pages/Book';
import BookingDone from './pages/BookingDone';
import MyAppointments from './pages/MyAppointments';
import { AuthProvider } from './auth/AuthContext';
import RequireAuth from './auth/RequireAuth';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="services" element={<Services />} />
          <Route path="equipe" element={<Team />} />
          <Route path="disponibilites" element={<Availability />} />
          <Route path="mot-de-passe-oublie" element={<ForgotPassword />} />
          <Route path="reinitialiser-mot-de-passe" element={<ResetPassword />} />
          <Route path="verify-email" element={<VerifyEmail />} />
          <Route path="connexion" element={<Login />} />
          <Route path="inscription" element={<Register />} />
          <Route
            path="reserver"
            element={
              <RequireAuth needRole="patient">
                <Book />
              </RequireAuth>
            }
          />
          <Route
            path="reserver/termine"
            element={
              <RequireAuth needRole="patient">
                <BookingDone />
              </RequireAuth>
            }
          />
          <Route
            path="mes-rendez-vous"
            element={
              <RequireAuth needRole="patient">
                <MyAppointments />
              </RequireAuth>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
