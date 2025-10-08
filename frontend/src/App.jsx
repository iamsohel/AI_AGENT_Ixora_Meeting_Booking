import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Create session on mount
  useEffect(() => {
    createSession()
  }, [])

  const createSession = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/session`)
      setSessionId(response.data.session_id)
      // Add welcome message
      setMessages([{
        type: 'agent',
        text: "Welcome! I am iXora AI Assistant. I'm here to help you book a meeting with Ixora Solution's CEO and CTO. What date and time would work best for you?",
        timestamp: new Date().toISOString()
      }])
    } catch (error) {
      console.error('Error creating session:', error)
      setMessages([{
        type: 'error',
        text: 'Failed to connect to the server. Please refresh the page.',
        timestamp: new Date().toISOString()
      }])
    }
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!inputMessage.trim() || !sessionId || isLoading) return

    const userMessage = inputMessage.trim()
    setInputMessage('')

    // Add user message to chat
    setMessages(prev => [...prev, {
      type: 'user',
      text: userMessage,
      timestamp: new Date().toISOString()
    }])

    setIsLoading(true)

    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        message: userMessage,
        session_id: sessionId
      })

      // Add agent response
      setMessages(prev => [...prev, {
        type: 'agent',
        text: response.data.message,
        timestamp: response.data.timestamp
      }])
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, {
        type: 'error',
        text: 'Sorry, there was an error processing your message. Please try again.',
        timestamp: new Date().toISOString()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const resetChat = async () => {
    if (!sessionId) return

    try {
      await axios.post(`${API_BASE_URL}/api/reset`, { session_id: sessionId })
      setMessages([{
        type: 'agent',
        text: "Conversation reset. What date and time would work best for you?",
        timestamp: new Date().toISOString()
      }])
    } catch (error) {
      console.error('Error resetting chat:', error)
    }
  }

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="app">
      <div className="chat-container">
        {/* Header */}
        <div className="chat-header">
          <div className="header-content">
            <h1>🤖 Ixora Meeting Booking</h1>
            <p>AI-Powered Scheduling Assistant</p>
          </div>
          <button onClick={resetChat} className="reset-btn" title="Reset conversation">
            ↻ Reset
          </button>
        </div>

        {/* Messages */}
        <div className="messages-container">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.type}`}>
              <div className="message-content">
                <div className="message-text">{msg.text}</div>
                <div className="message-time">{formatTimestamp(msg.timestamp)}</div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message agent">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={sendMessage} className="input-container">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type your message..."
            disabled={!sessionId || isLoading}
            className="message-input"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || !sessionId || isLoading}
            className="send-btn"
          >
            Send ➤
          </button>
        </form>
      </div>
    </div>
  )
}

export default App
