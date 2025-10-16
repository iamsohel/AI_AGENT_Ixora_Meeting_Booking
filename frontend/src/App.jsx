import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ChatWidget from './components/ChatWidget';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import ChatDetail from './pages/ChatDetail';
import AdminLayout from './layouts/AdminLayout';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Home route with chat widget */}
          <Route path="/" element={<ChatWidget />} />

          {/* Admin login */}
          <Route path="/login" element={<Login />} />

          {/* Protected admin routes with shared layout */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            {/* Admin dashboard - index route */}
            <Route index element={<AdminDashboard />} />

            {/* Chat detail page - nested route */}
            <Route path="chat/:sessionId" element={<ChatDetail />} />
          </Route>

          {/* Catch all - redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
