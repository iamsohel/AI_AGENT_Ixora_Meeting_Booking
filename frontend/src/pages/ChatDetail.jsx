import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '../contexts/AuthContext';
import '../styles/ChatDetail.css';

const ChatDetail = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { token, logout } = useAuth();
  const [chatData, setChatData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE_URL = 'http://10.5.5.116:8000';

  useEffect(() => {
    loadChatDetails();
  }, [sessionId]);

  const loadChatDetails = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/admin/chats/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setChatData(response.data);
    } catch (error) {
      console.error('Error loading chat details:', error);
      if (error.response?.status === 401) {
        logout();
        navigate('/login');
      } else {
        setError('Failed to load chat details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/admin');
  };

  if (loading) {
    return (
      <div className="chat-detail-page">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading conversation details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chat-detail-page">
        <div className="error-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3>Error Loading Chat</h3>
          <p>{error}</p>
          <button onClick={handleBack} className="back-button-primary">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!chatData) {
    return null;
  }

  return (
    <div className="chat-detail-page">
      {/* Header with Back Button */}
      <div className="detail-header">
        <button onClick={handleBack} className="back-button">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Dashboard
        </button>
        <h1>Conversation Details</h1>
      </div>

      <div className="chat-detail-content">
        {/* Session Information Card */}
        <div className="session-info-card">
          <div className="card-header">
            <div className="header-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2>Session Information</h2>
          </div>

          <div className="info-grid">
            <div className="info-item">
              <div className="info-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                </svg>
              </div>
              <div className="info-content">
                <label>Session ID</label>
                <div className="value session-id">{chatData.session.id}</div>
              </div>
            </div>

            <div className="info-item">
              <div className="info-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div className="info-content">
                <label>Agent Mode</label>
                <div className="value">
                  {chatData.session.agent_mode ? (
                    <span className={`badge badge-${chatData.session.agent_mode}`}>
                      {chatData.session.agent_mode.toUpperCase()}
                    </span>
                  ) : (
                    <span className="value-text">N/A</span>
                  )}
                </div>
              </div>
            </div>

            <div className="info-item">
              <div className="info-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="info-content">
                <label>Booking Status</label>
                <div className="value">
                  {chatData.session.booking_completed ? (
                    <span className="badge badge-success">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                      </svg>
                      COMPLETED
                    </span>
                  ) : (
                    <span className="status-inactive">Not Completed</span>
                  )}
                </div>
              </div>
            </div>

            <div className="info-item">
              <div className="info-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
              </div>
              <div className="info-content">
                <label>Total Messages</label>
                <div className="value value-number">{chatData.messages.length}</div>
              </div>
            </div>

            <div className="info-item">
              <div className="info-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="info-content">
                <label>Created At</label>
                <div className="value value-time">
                  {new Date(chatData.session.created_at).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            </div>

            <div className="info-item">
              <div className="info-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <div className="info-content">
                <label>Last Updated</label>
                <div className="value value-time">
                  {new Date(chatData.session.updated_at).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Messages Section */}
        <div className="messages-section">
          <div className="section-header">
            <div className="header-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <div>
              <h2>Conversation Timeline</h2>
              <p className="section-subtitle">{chatData.messages.length} messages in this conversation</p>
            </div>
          </div>

          <div className="messages-container">
            {chatData.messages.map((msg, index) => (
              <div key={index} className={`message-bubble ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  )}
                </div>
                <div className="message-wrapper">
                  <div className="message-header">
                    <span className="message-role">
                      {msg.role === 'user' ? 'Customer' : 'AI Assistant'}
                    </span>
                    <span className="message-index">#{index + 1}</span>
                  </div>
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      <p>{msg.content}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatDetail;
