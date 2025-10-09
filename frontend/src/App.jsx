import axios from "axios";
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://10.5.5.116:8000";

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Create session on mount
  useEffect(() => {
    createSession();
  }, []);

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  // Auto-focus input when chat opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Auto-focus input after response is complete
  useEffect(() => {
    if (!isLoading && inputRef.current && isOpen) {
      // Small delay to ensure DOM is updated
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [isLoading, isOpen]);

  const createSession = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/session`);
      setSessionId(response.data.session_id);
      // Add welcome message
      setMessages([
        {
          type: "agent",
          text: "Hi! I'm your iXora AI assistant 👋\n\nI can help you schedule a meeting with our CEO and CTO. Simply tell me your preferred date and time.\n\nWhen would you like to meet?",
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error("Error creating session:", error);
      setMessages([
        {
          type: "error",
          text: "Failed to connect to the server. Please refresh the page.",
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || !sessionId || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage("");

    // Add user message to chat
    setMessages((prev) => [
      ...prev,
      {
        type: "user",
        text: userMessage,
        timestamp: new Date().toISOString(),
      },
    ]);

    setIsLoading(true);

    // Add placeholder for streaming response
    const streamingMessageId = Date.now();
    setMessages((prev) => [
      ...prev,
      {
        type: "agent",
        text: "",
        timestamp: new Date().toISOString(),
        isStreaming: true,
        id: streamingMessageId,
      },
    ]);

    try {
      // Use fetch for SSE streaming
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to connect to streaming endpoint");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");

        // Process complete lines
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();

          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.substring(6));

            if (data.error) {
              // Handle error
              setStatusMessage("");
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingMessageId
                    ? {
                        ...msg,
                        text: `Error: ${data.error}`,
                        type: "error",
                        isStreaming: false,
                      }
                    : msg
                )
              );
              break;
            } else if (data.done) {
              // Streaming complete
              setStatusMessage("");
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingMessageId
                    ? { ...msg, isStreaming: false }
                    : msg
                )
              );
              break;
            } else if (data.status !== undefined) {
              // Update status message
              setStatusMessage(data.status);
            } else if (data.chunk) {
              // Append chunk to message
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingMessageId
                    ? { ...msg, text: msg.text + data.chunk }
                    : msg
                )
              );
            }
          }
        }

        // Keep the last incomplete line in buffer
        buffer = lines[lines.length - 1];
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setStatusMessage("");
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === streamingMessageId
            ? {
                ...msg,
                text: "Sorry, there was an error processing your message. Please try again.",
                type: "error",
                isStreaming: false,
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      setStatusMessage("");
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="app">
      {/* Floating Chat Button */}
      <button
        className={`chat-button ${isOpen ? "open" : ""}`}
        onClick={toggleChat}
        aria-label={isOpen ? "Close chat" : "Open chat"}
      >
        <svg
          className="chat-icon"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
        <svg
          className="close-icon"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      {/* Chat Container */}
      <div className={`chat-container ${isOpen ? "open" : ""}`}>
        {/* Header */}
        <div className="chat-header">
          <div className="header-content">
            <h1>
              <span className="brand-icon">✦</span> iXora AI Assistant
            </h1>
            <p>Book a meeting with our leadership</p>
          </div>
        </div>

        {/* Messages */}
        <div className="messages-container">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.type}`}>
              <div className="message-content">
                <div className="message-text">
                  {msg.text}
                  {msg.isStreaming && statusMessage && (
                    <div className="status-message">
                      <span className="status-icon">⏳</span> {statusMessage}
                    </div>
                  )}
                  {msg.isStreaming && !statusMessage && msg.text && (
                    <span className="typing-cursor">▊</span>
                  )}
                </div>
                <div className="message-time">
                  {formatTimestamp(msg.timestamp)}
                </div>
              </div>
            </div>
          ))}
          {isLoading && !messages.some((msg) => msg.isStreaming) && (
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
          <div className="input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask me anything..."
              disabled={!sessionId || isLoading}
              className="message-input"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (inputMessage.trim() && sessionId && !isLoading) {
                    sendMessage(e);
                  }
                }
              }}
            />
            {inputMessage.trim() && (
              <button
                type="submit"
                disabled={!sessionId || isLoading}
                className="send-icon-btn"
                aria-label="Send message"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default App;
