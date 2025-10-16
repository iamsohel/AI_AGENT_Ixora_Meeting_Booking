import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../styles/AdminLayout.css';

const AdminLayout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <div className="admin-layout">
      <header className="admin-header">
        <div className="admin-header-container">
          {/* Logo Section */}
          <div className="admin-logo" onClick={() => navigate('/admin')}>
            <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
              <path d="M50 10 L90 50 L50 90 L10 50 Z" fill="#E31E24" />
              <path d="M50 30 L70 50 L50 70 L30 50 Z" fill="white" />
            </svg>
            <div className="admin-logo-text">
              <span className="logo-main">IXORA</span>
              <span className="logo-sub">Admin Panel</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="admin-nav">
            <button
              className={`nav-item ${isActive('/admin') ? 'active' : ''}`}
              onClick={() => navigate('/admin')}
            >
              Dashboard
            </button>
            <button
              className={`nav-item ${location.pathname.includes('/admin/chat') ? 'active' : ''}`}
            >
              Sessions
            </button>
            <button className="nav-item">Analytics</button>
          </nav>

          {/* User Section */}
          <div className="admin-user-section">
            <div className="admin-user-info">
              <div className="user-avatar">
                {(user?.username || 'A').charAt(0).toUpperCase()}
              </div>
              <span className="user-name">{user?.username || 'Admin'}</span>
            </div>
            <button onClick={handleLogout} className="logout-button">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="admin-content">
        <Outlet />
      </div>
    </div>
  );
};

export default AdminLayout;
