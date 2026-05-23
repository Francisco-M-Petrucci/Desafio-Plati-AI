import React, { useState } from 'react';
import axios from 'axios';
import { ChefHat, ArrowRight, Sparkles } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function Login({ onLoginSuccess, onRegisterToggle }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('password123'); // Default password for easy demo
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('Please enter a username');
      return;
    }
    setError('');
    setIsLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/auth/login`, {
        username: username.trim(),
        password: password
      });
      onLoginSuccess(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed. Please check backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePresetLogin = async (presetUser) => {
    setIsLoading(true);
    setError('');
    try {
      const res = await axios.post(`${API_BASE}/api/auth/login`, {
        username: presetUser,
        password: 'password123'
      });
      onLoginSuccess(res.data);
    } catch (err) {
      setError(`Failed to connect as ${presetUser}. Is the backend server running?`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div style={{ display: 'inline-flex', padding: '0.75rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '14px', marginBottom: '1rem', color: 'hsl(var(--primary))' }}>
            <ChefHat size={40} strokeWidth={2} />
          </div>
          <h1 className="login-title">ChefCompanion</h1>
          <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem' }}>
            Your AI assistant for hyper-personalized recipe ideas and smart kitchen inventory.
          </p>
        </div>

        {error && (
          <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.2)', padding: '0.75rem', borderRadius: '8px', color: '#fda4af', fontSize: '0.85rem', marginBottom: '1.25rem', textAlign: 'center' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">Username</label>
            <input 
              id="username"
              type="text" 
              className="form-input" 
              placeholder="e.g. julia_child" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label className="form-label" htmlFor="password">Password</label>
            <input 
              id="password"
              type="password" 
              className="form-input" 
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary" 
            style={{ width: '100%', justifyContent: 'center', padding: '0.8rem', borderRadius: '10px', fontSize: '1rem', marginTop: '1rem' }}
            disabled={isLoading}
          >
            <span>{isLoading ? 'Connecting...' : 'Enter Kitchen'}</span>
            <ArrowRight size={18} />
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.85rem', color: 'hsl(var(--text-secondary))' }}>
          Don't have an account?{' '}
          <button 
            type="button" 
            onClick={onRegisterToggle} 
            style={{ background: 'transparent', border: 'none', color: 'hsl(var(--primary))', fontWeight: '600', cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
          >
            Create Account
          </button>
        </div>

        <div className="login-presets">
          <div className="presets-title">
            <Sparkles size={12} style={{ marginRight: '0.25rem', display: 'inline' }} />
            Try Seeding Test Personas
          </div>
          
          <div className="presets-buttons">
            <button type="button" onClick={() => handlePresetLogin('alice')} disabled={isLoading}>
              Alice (Gluten-Free)
            </button>
            <button type="button" onClick={() => handlePresetLogin('bob')} disabled={isLoading}>
              Bob (Vegetarian)
            </button>
          </div>
          <p style={{ color: 'hsl(var(--text-muted))', fontSize: '0.75rem', textAlign: 'center', marginTop: '0.75rem' }}>
            Preset accounts are seeded with distinct ingredients, restrictions, and long-term memory facts.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
