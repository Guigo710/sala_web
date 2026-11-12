import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Carregando from './components/Carregando';
import RotaProtegida from './auth/RotaProtegida';
import RotaAdmin from './auth/RotaAdmin';
import Login from './pages/Login';
import Salas from './pages/Salas';
import SalaDetalhe from './pages/SalaDetalhe';
import MinhasReservas from './pages/MinhasReservas';
import MinhaConta from './pages/MinhaConta';
import NaoEncontrada from './pages/NaoEncontrada';

// FullCalendar e o painel admin ficam em pedaços separados do bundle.
const Agenda = lazy(() => import('./pages/Agenda'));
const AdminLayout = lazy(() => import('./pages/admin/AdminLayout'));
const AdminSalas = lazy(() => import('./pages/admin/AdminSalas'));
const AdminSalaEditar = lazy(() => import('./pages/admin/AdminSalaEditar'));
const AdminEquipamentos = lazy(() => import('./pages/admin/AdminEquipamentos'));
const AdminSoftwares = lazy(() => import('./pages/admin/AdminSoftwares'));
const AdminProfessores = lazy(() => import('./pages/admin/AdminProfessores'));
const AdminHorarios = lazy(() => import('./pages/admin/AdminHorarios'));
const AdminSemestres = lazy(() => import('./pages/admin/AdminSemestres'));

export default function App() {
  return (
    <Suspense fallback={<Carregando />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/agenda" replace />} />
          <Route path="agenda" element={<Agenda />} />
          <Route path="ambientes" element={<Salas />} />
          <Route path="ambientes/:id" element={<SalaDetalhe />} />
          <Route path="login" element={<Login />} />
          <Route
            path="minhas-reservas"
            element={
              <RotaProtegida>
                <MinhasReservas />
              </RotaProtegida>
            }
          />
          <Route
            path="minha-conta"
            element={
              <RotaProtegida>
                <MinhaConta />
              </RotaProtegida>
            }
          />
          <Route
            path="admin"
            element={
              <RotaAdmin>
                <AdminLayout />
              </RotaAdmin>
            }
          >
            <Route index element={<Navigate to="ambientes" replace />} />
            <Route path="ambientes" element={<AdminSalas />} />
            <Route path="ambientes/novo" element={<AdminSalaEditar />} />
            <Route path="ambientes/:id" element={<AdminSalaEditar />} />
            <Route path="equipamentos" element={<AdminEquipamentos />} />
            <Route path="softwares" element={<AdminSoftwares />} />
            <Route path="professores" element={<AdminProfessores />} />
            <Route path="horarios" element={<AdminHorarios />} />
            <Route path="semestres" element={<AdminSemestres />} />
          </Route>
          <Route path="*" element={<NaoEncontrada />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
