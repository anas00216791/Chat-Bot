import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from '@docusaurus/router';
import './RagChatbot.css';

const ModulesChatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedText, setSelectedText] = useState(null);
  const [mode, setMode] = useState('book_scope');
  const messagesEndRef = useRef(null);
  const location = useLocation();

  // Detect current module from URL path
  const getCurrentModule = () => {
    const path = location.pathname;

    // Match module patterns: /module-1-ros2, /module-2-gazebo-unity, etc.
    const moduleMatch = path.match(/\/(module-\d+-[^\/]+)/);
    if (moduleMatch) {
      return moduleMatch[1];
    }

    // Check if on intro page
    if (path === '/intro' || path === '/') {
      return 'intro';
    }

    return null;
  };

  const currentModule = getCurrentModule();

  // Get friendly module name for UI
  const getModuleName = () => {
    if (!currentModule) return 'Book';

    const moduleNames = {
      'intro': 'Introduction',
      'module-1-ros2': 'Module 1: ROS 2',
      'module-2-gazebo-unity': 'Module 2: Gazebo & Unity',
      'module-3-isaac-sim': 'Module 3: Isaac Sim',
      'module-4-vla': 'Module 4: VLA Models'
    };

    return moduleNames[currentModule] || 'Module';
  };

  // Function to get selected text from the page
  useEffect(() => {
    const handleSelection = () => {
      const selectedText = window.getSelection().toString().trim();
      if (selectedText.length > 0) {
        setSelectedText(selectedText);
        setMode('selected_text_only');
      } else {
        setMode('book_scope');
      }
    };

    document.addEventListener('mouseup', handleSelection);
    return () => {
      document.removeEventListener('mouseup', handleSelection);
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage = { text: inputText, sender: 'user', timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // Determine the query payload based on mode
      const queryPayload = {
        query: inputText,
        mode: mode,
        module: currentModule // Send current module for prioritization
      };

      if (mode === 'selected_text_only' && selectedText) {
        queryPayload.selected_text = selectedText;
      }

      // Call the RAG backend API
      // Use environment-aware API URL
      const apiUrl = typeof window !== 'undefined' && window.location.origin.includes('vercel.app')
        ? `${window.location.origin}/api/rag/query`
        : 'http://localhost:5000/api/rag/query';

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(queryPayload)
      });

      const data = await response.json();

      if (data.success) {
        const botMessage = {
          text: data.answer,
          sender: 'bot',
          sources: data.sources || [],
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        const errorMessage = {
          text: data.answer || 'Sorry, I could not process your request.',
          sender: 'bot',
          error: true,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        text: 'Sorry, there was an error connecting to the chatbot. Please try again.',
        sender: 'bot',
        error: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  const clearChat = () => {
    setMessages([]);
  };

  const moduleName = getModuleName();

  return (
    <div className="rag-chatbot">
      {isOpen ? (
        <div className="chat-container">
          <div className="chat-header">
            <div className="chat-title">{moduleName} Assistant</div>
            <div className="chat-controls">
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="mode-selector"
                disabled={isLoading}
              >
                <option value="book_scope">All Content</option>
                <option value="selected_text_only">Selected Text Only</option>
              </select>
              <button onClick={clearChat} className="clear-btn" disabled={isLoading}>Clear</button>
              <button onClick={toggleChat} className="close-btn">✕</button>
            </div>
          </div>

          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="welcome-message">
                <p>Hello! I'm your {moduleName} assistant.</p>
                <p>• Ask questions about {moduleName.toLowerCase()} content</p>
                <p>• I prioritize content from this module but can search across all modules</p>
                <p>• Select text on the page and ask specific questions</p>
                {selectedText && (
                  <div className="selected-text-preview">
                    <small>Selected: "{selectedText.substring(0, 50)}..."</small>
                  </div>
                )}
              </div>
            ) : (
              messages.map((msg, index) => (
                <div key={index} className={`message ${msg.sender}`}>
                  <div className="message-content">
                    <div className="message-text">{msg.text}</div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="message-sources">
                        Sources: {msg.sources.join(', ')}
                      </div>
                    )}
                    {msg.error && (
                      <div className="message-error">
                        This response may be limited due to unavailable information in the provided text.
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="message bot">
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

          <div className="chat-input-area">
            {mode === 'selected_text_only' && selectedText && (
              <div className="selected-text-indicator">
                Using selected text: "{selectedText.substring(0, 60)}{selectedText.length > 60 ? '...' : ''}"
              </div>
            )}
            <div className="input-container">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={mode === 'selected_text_only' ? "Ask about the selected text..." : `Ask about ${moduleName.toLowerCase()} content...`}
                className="chat-input"
                disabled={isLoading}
                rows="1"
              />
              <button
                onClick={sendMessage}
                className="send-btn"
                disabled={!inputText.trim() || isLoading}
              >
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button className="chat-toggle-btn" onClick={toggleChat}>
          <span className="chat-icon">🤖</span>
          <span className="chat-text">Ask Assistant</span>
        </button>
      )}
    </div>
  );
};

export default ModulesChatbot;
