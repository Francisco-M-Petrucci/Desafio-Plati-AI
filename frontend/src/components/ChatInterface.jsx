import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Upload, FileImage, Sparkles, Trash2, ArrowRight, Loader2, Plus, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function ChatInterface({ user, profile, onProfileUpdate }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  
  // Scanned receipt items staging area
  const [scannedItems, setScannedItems] = useState(null);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchChatHistory();
  }, [user]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const fetchChatHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/users/${user.user_id}/chat-history`);
      setMessages(res.data);
    } catch (err) {
      console.error("Error fetching chat history:", err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const userMessageText = input.trim();
    setInput('');
    setIsSending(true);

    // Optimistically update message history list in state
    setMessages(prev => [...prev, { role: 'user', content: userMessageText }]);

    try {
      const res = await axios.post(`${API_BASE}/api/chat`, {
        user_id: user.user_id,
        message: userMessageText
      });

      // Update state with AI response
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
      
      // If the AI modified ingredients or added a fact, update profile state
      if (res.data.actions && res.data.actions.length > 0) {
        onProfileUpdate();
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Sorry, I encountered an error running the agent. ${err.response?.data?.detail || ''}. Please check if NVIDIA_API_KEY is configured in your .env file.` 
      }]);
    } finally {
      setIsSending(false);
    }
  };

  // Receipt image upload handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadReceiptFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadReceiptFile(e.target.files[0]);
    }
  };

  const uploadReceiptFile = async (file) => {
    setIsUploading(true);
    setScannedItems(null);
    const formData = new FormData();
    formData.append("user_id", user.user_id);
    formData.append("file", file);

    try {
      const res = await axios.post(`${API_BASE}/api/receipts/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setScannedItems(res.data.ingredients);
    } catch (err) {
      console.error(err);
      alert("Failed to parse receipt image. " + (err.response?.data?.detail || ""));
    } finally {
      setIsUploading(false);
    }
  };

  const handleConfirmAddScanned = async () => {
    if (!scannedItems || scannedItems.length === 0) return;
    setIsUploading(true);

    // Merge scanned items with user's existing inventory
    const merged = [...profile.ingredients];
    
    scannedItems.forEach(scanned => {
      const idx = merged.findIndex(existing => existing.name.toLowerCase() === scanned.name.toLowerCase());
      if (idx >= 0) {
        merged[idx].quantity += scanned.quantity;
      } else {
        merged.push({
          name: scanned.name.toLowerCase(),
          quantity: scanned.quantity,
          unit: scanned.unit.toLowerCase()
        });
      }
    });

    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/ingredients`, {
        ingredients: merged
      });
      
      // Post an artificial AI notice about the upload to the conversation history database
      const itemsListStr = scannedItems.map(i => `+${i.quantity} ${i.unit} of ${i.name}`).join(", ");
      const messageText = `I uploaded a shopping receipt. The system successfully added these ingredients to my kitchen: ${itemsListStr}`;
      
      setMessages(prev => [...prev, { role: 'user', content: `[Receipt Uploaded]` }]);
      
      const chatResponse = await axios.post(`${API_BASE}/api/chat`, {
        user_id: user.user_id,
        message: messageText
      });

      setMessages(prev => [...prev, { role: 'assistant', content: chatResponse.data.response }]);
      
      setScannedItems(null);
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClearChat = async () => {
    if (!window.confirm("Clear all conversation history?")) return;
    try {
      await axios.delete(`${API_BASE}/api/users/${user.user_id}/chat-history`);
      setMessages([]);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', width: '100%', margin: '0 auto', flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
      <div className="chat-container">
        
        {/* Chat Header */}
        <div className="chat-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ height: '8px', width: '8px', background: 'hsl(var(--primary))', borderRadius: '50%', display: 'inline-block' }}></span>
            <span style={{ fontSize: '0.95rem', fontWeight: '600' }}>Active Session: Hyper-Personalized AI</span>
          </div>
          {messages.length > 0 && (
            <button 
              onClick={handleClearChat}
              className="btn-danger"
              style={{ padding: '0.4rem 0.8rem', borderRadius: '6px', fontSize: '0.75rem' }}
            >
              <Trash2 size={12} />
              <span>Clear History</span>
            </button>
          )}
        </div>

        {/* Message History Grid */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div style={{ margin: 'auto', textAlign: 'center', maxWidth: '460px', padding: '2rem' }}>
              <div style={{ display: 'inline-flex', padding: '1rem', background: 'rgba(139, 92, 246, 0.08)', borderRadius: '50%', marginBottom: '1.25rem', color: 'hsl(var(--secondary))' }}>
                <Sparkles size={36} />
              </div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: '700', marginBottom: '0.5rem' }}>
                How can I help you cook today?
              </h2>
              <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem', lineHeight: '1.5' }}>
                Try asking for a recipe based on what you have! Or update ingredients directly.
              </p>
              <p style={{ color: 'hsl(var(--text-muted))', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                Examples:<br />
                <em>"What can I cook with the ingredients I have?"</em><br />
                <em>"I just bought 2 tomatoes and some spinach."</em>
              </p>
            </div>
          ) : (
            messages.map((msg, index) => {
              if (msg.content === '[Receipt Uploaded]') return null;
              return (
                <div 
                  key={index} 
                  className={`message-bubble ${msg.role === 'user' ? 'message-user' : 'message-ai'}`}
                >
                  {msg.content}
                </div>
              );
            })
          )}
          {isSending && (
            <div className="message-bubble message-ai" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Loader2 size={16} className="pulse" style={{ animation: 'spin 1s linear infinite' }} />
              <span>Chef is thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Staging Drawer: Scanned items from receipt */}
        {scannedItems && (
          <div style={{ background: 'rgba(16, 185, 129, 0.08)', borderTop: '1px solid hsl(var(--primary) / 0.25)', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'hsl(var(--primary))', fontWeight: '600', fontSize: '0.95rem' }}>
                <Sparkles size={16} />
                <span>Ingredients Scanned from Receipt:</span>
              </div>
              <button 
                onClick={() => setScannedItems(null)}
                style={{ background: 'transparent', color: 'hsl(var(--text-muted))' }}
              >
                <X size={16} />
              </button>
            </div>
            
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {scannedItems.map((item, idx) => (
                <span 
                  key={idx} 
                  style={{ 
                    fontSize: '0.8rem', 
                    padding: '0.3rem 0.6rem', 
                    background: 'rgba(16, 185, 129, 0.15)', 
                    border: '1px solid hsl(var(--primary) / 0.3)', 
                    borderRadius: '6px',
                    color: '#fff',
                    textTransform: 'capitalize'
                  }}
                >
                  +{item.quantity} {item.unit} {item.name}
                </span>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem' }}>
              <button 
                className="btn-primary" 
                onClick={handleConfirmAddScanned}
                disabled={isUploading}
                style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
              >
                <Plus size={14} />
                <span>Add All to Pantry Inventory</span>
              </button>
              <button 
                className="btn-secondary" 
                onClick={() => setScannedItems(null)}
                style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                disabled={isUploading}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Input Panel and Receipt Scanner */}
        <div className="chat-input-area">
          <form onSubmit={handleSend} className="chat-input-row">
            <input 
              type="text" 
              className="chat-input" 
              placeholder="Ask for recipe ideas or type ingredient updates..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isSending || isUploading}
            />
            <button 
              type="submit" 
              className="btn-primary" 
              style={{ borderRadius: '14px', width: '48px', height: '48px', padding: 0, justifyContent: 'center' }}
              disabled={isSending || isUploading || !input.trim()}
            >
              <Send size={18} />
            </button>
          </form>

          {/* Drag & Drop Receipt Zone */}
          <div 
            className={`receipt-upload-zone ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept="image/*"
              onChange={handleFileChange}
              disabled={isUploading || isSending}
            />
            
            {isUploading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'hsl(var(--primary))' }}>
                <Loader2 size={18} className="pulse" style={{ animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '0.85rem', fontWeight: '500' }}>Analyzing Receipt with Llama 3.2 Vision...</span>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'hsl(var(--text-secondary))' }}>
                <Upload size={16} />
                <span style={{ fontSize: '0.85rem' }}>
                  <strong>Upload shopping receipt photo</strong> or drag & drop to auto-extract ingredients (PNG/JPG)
                </span>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

export default ChatInterface;
