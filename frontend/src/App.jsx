import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ChefHat, MessageSquare, LayoutDashboard, Utensils, LogOut } from 'lucide-react';
import Login from './pages/Login';
import RegisterWizard from './pages/RegisterWizard';
import ChatInterface from './components/ChatInterface';
import ProfileManager from './components/ProfileManager';
import RecipeBrowser from './components/RecipeBrowser';

const API_BASE = 'http://localhost:8000';

function App() {
  const [user, setUser] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'dashboard' | 'recipes'
  const [profile, setProfile] = useState({
    ingredients: [],
    appliances: [],
    restrictions: [],
    facts: [],
    temporary_preferences: []
  });
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);

  // Load saved user from local storage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('recipe_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  // Fetch user profile whenever user changes
  useEffect(() => {
    if (user) {
      if (user.access_token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${user.access_token}`;
      }
      fetchProfile();
    } else {
      delete axios.defaults.headers.common['Authorization'];
      setProfile({
        ingredients: [],
        appliances: [],
        restrictions: [],
        facts: [],
        temporary_preferences: []
      });
    }
  }, [user]);

  const fetchProfile = async () => {
    if (!user) return;
    setIsLoadingProfile(true);
    try {
      const res = await axios.get(`${API_BASE}/api/users/${user.user_id}/profile`);
      setProfile(res.data);
    } catch (err) {
      console.error("Error fetching user profile:", err);
    } finally {
      setIsLoadingProfile(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('recipe_user');
    setUser(null);
    setActiveTab('chat');
  };

  if (!user) {
    if (isRegistering) {
      return (
        <RegisterWizard 
          onRegisterSuccess={(u) => {
            localStorage.setItem('recipe_user', JSON.stringify(u));
            setUser(u);
            setIsRegistering(false);
          }}
          onCancel={() => setIsRegistering(false)}
        />
      );
    }
    return (
      <Login 
        onLoginSuccess={(u) => {
          localStorage.setItem('recipe_user', JSON.stringify(u));
          setUser(u);
        }} 
        onRegisterToggle={() => setIsRegistering(true)}
      />
    );
  }

  return (
    <div className="app-container">
      {/* Navigation Bar */}
      <header className="navbar">
        <div className="brand">
          <ChefHat size={32} strokeWidth={2.5} style={{ color: 'hsl(var(--primary))' }} />
          <span>ChefCompanion</span>
        </div>
        
        <nav className="nav-actions">
          <button 
            className={`btn-secondary ${activeTab === 'chat' ? 'active-nav' : ''}`}
            onClick={() => setActiveTab('chat')}
            style={{ 
              borderColor: activeTab === 'chat' ? 'hsl(var(--primary))' : 'transparent',
              background: activeTab === 'chat' ? 'rgba(16, 185, 129, 0.08)' : ''
            }}
          >
            <MessageSquare size={18} />
            <span>Assistant Chat</span>
          </button>
          
          <button 
            className={`btn-secondary ${activeTab === 'dashboard' ? 'active-nav' : ''}`}
            onClick={() => setActiveTab('dashboard')}
            style={{ 
              borderColor: activeTab === 'dashboard' ? 'hsl(var(--primary))' : 'transparent',
              background: activeTab === 'dashboard' ? 'rgba(16, 185, 129, 0.08)' : ''
            }}
          >
            <LayoutDashboard size={18} />
            <span>My Kitchen</span>
          </button>
          
          <button 
            className={`btn-secondary ${activeTab === 'recipes' ? 'active-nav' : ''}`}
            onClick={() => setActiveTab('recipes')}
            style={{ 
              borderColor: activeTab === 'recipes' ? 'hsl(var(--primary))' : 'transparent',
              background: activeTab === 'recipes' ? 'rgba(16, 185, 129, 0.08)' : ''
            }}
          >
            <Utensils size={18} />
            <span>Recipe Explorer</span>
          </button>

          <div style={{ width: '1px', height: '24px', background: 'hsl(var(--border))', margin: '0 0.5rem' }}></div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.875rem', color: 'hsl(var(--text-secondary))' }}>
              Hi, <strong style={{ color: '#fff' }}>{user.username}</strong>
            </span>
            <button className="btn-danger" onClick={handleLogout} title="Logout">
              <LogOut size={16} />
            </button>
          </div>
        </nav>
      </header>

      {/* Main Content Area */}
      <main style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'chat' && (
          <ChatInterface 
            user={user} 
            profile={profile} 
            onProfileUpdate={fetchProfile} 
          />
        )}
        
        {activeTab === 'dashboard' && (
          <ProfileManager 
            user={user} 
            profile={profile} 
            isLoading={isLoadingProfile}
            onProfileUpdate={fetchProfile} 
          />
        )}
        
        {activeTab === 'recipes' && (
          <RecipeBrowser 
            user={user} 
            profile={profile}
          />
        )}
      </main>
    </div>
  );
}

export default App;
