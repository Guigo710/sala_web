import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import App from './App';
import { AuthProvider } from './auth/AuthContext';
import AvisosProvider from './components/AvisosProvider';
import './styles/global.css';

async function iniciar() {
  // Mock opcional, só em desenvolvimento (VITE_USE_MOCK=true). Em `vite build`,
  // import.meta.env.DEV é false e este bloco (com o mock) sai do bundle.
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === 'true') {
    const { instalarMock } = await import('./api/mock/servidor.js');
    instalarMock();
  }

  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <BrowserRouter>
        <AuthProvider>
          <AvisosProvider>
            <App />
          </AvisosProvider>
        </AuthProvider>
      </BrowserRouter>
    </StrictMode>,
  );
}

iniciar();
