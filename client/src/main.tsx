import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import App from './App';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="bottom-right"
        closeButton
        toastOptions={{
          style: {
            background: '#f3f4f6',
            color: '#1f2937',
            border: '1px solid #d1d5db',
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
);
