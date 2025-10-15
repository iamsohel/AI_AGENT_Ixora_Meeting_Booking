import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import '../styles/AdminDashboard.css';

const AdminDashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [activeTab, setActiveTab] = useState('chats');
  const [loading, setLoading] = useState(true);
  const { user, logout, token } = useAuth();
  const navigate = useNavigate();

  const API_BASE_URL = 'http://10.5.5.116:8000';

  useEffect(() => {
    loadAnalytics();
    loadChats();
  }, []);

  const loadAnalytics = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/analytics`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error loading analytics:', error);
      if (error.response?.status === 401) {
        logout();
        navigate('/login');
      }
    }
  };

  const loadChats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/chats?limit=50`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setChats(response.data);
    } catch (error) {
      console.error('Error loading chats:', error);
      if (error.response?.status === 401) {
        logout();
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const viewChat = async (sessionId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/chats/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedChat(response.data);
    } catch (error) {
      console.error('Error loading chat details:', error);
      if (error.response?.status === 401) {
        logout();
        navigate('/login');
      }
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="admin-container">
      <header className="admin-header">
        <h1>iXora Admin Panel</h1>
        <div className="admin-header-right">
          <span className="admin-user">{user?.username || 'Admin'}</span>
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        </div>
      </header>

      {analytics && (
        <div className="analytics-cards">
          <div className="stat-card">
            <h3>Total Sessions</h3>
            <div className="stat-value">{analytics.total_sessions}</div>
          </div>
          <div className="stat-card">
            <h3>Total Messages</h3>
            <div className="stat-value">{analytics.total_messages}</div>
          </div>
          <div className="stat-card">
            <h3>RAG Sessions</h3>
            <div className="stat-value">{analytics.rag_sessions}</div>
          </div>
          <div className="stat-card">
            <h3>Booking Sessions</h3>
            <div className="stat-value">{analytics.booking_sessions}</div>
          </div>
          <div className="stat-card">
            <h3>Completed Bookings</h3>
            <div className="stat-value">{analytics.completed_bookings}</div>
          </div>
        </div>
      )}

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'chats' ? 'active' : ''}`}
          onClick={() => setActiveTab('chats')}
        >
          Chat Logs
        </button>
        <button
          className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </div>

      <div className="content-panel">
        {activeTab === 'chats' && (
          <div>
            <h2>Recent Conversations</h2>
            {loading ? (
              <div className="loading">Loading chats...</div>
            ) : (
              <>
                <div className="chat-list">
                  {chats.length === 0 ? (
                    <p>No chats found</p>
                  ) : (
                    chats.map((chat) => (
                      <div
                        key={chat.id}
                        className="chat-item"
                        onClick={() => viewChat(chat.id)}
                      >
                        <div className="chat-item-header">
                          <span className="chat-item-id">
                            {chat.id.substring(0, 8)}...
                          </span>
                          <span className="chat-item-time">
                            {new Date(chat.updated_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="chat-item-meta">
                          {chat.agent_mode && (
                            <span className={`badge badge-${chat.agent_mode}`}>
                              {chat.agent_mode.toUpperCase()}
                            </span>
                          )}
                          {chat.booking_completed && (
                            <span className="badge badge-success">BOOKED</span>
                          )}
                          <span>{chat.message_count} messages</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {selectedChat && (
                  <div className="message-view">
                    <h3>Conversation Details</h3>
                    <div className="chat-details">
                      <p>
                        <strong>Session:</strong> {selectedChat.session.id}
                      </p>
                      <p>
                        <strong>Mode:</strong>{' '}
                        {selectedChat.session.agent_mode || 'N/A'}
                      </p>
                      <p>
                        <strong>Booking Completed:</strong>{' '}
                        {selectedChat.session.booking_completed ? 'Yes' : 'No'}
                      </p>
                    </div>
                    <hr />
                    <div className="messages">
                      {selectedChat.messages.map((msg, index) => (
                        <div key={index} className={`message ${msg.role}`}>
                          <div className="message-role">{msg.role}</div>
                          <div className="message-content">{msg.content}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'analytics' && (
          <div>
            <h2>Detailed Analytics</h2>
            <p>Analytics dashboard coming soon...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
