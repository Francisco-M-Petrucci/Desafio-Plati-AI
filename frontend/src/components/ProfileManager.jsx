import React, { useState } from 'react';
import axios from 'axios';
import { Trash2, Plus, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const APPLIANCE_OPTIONS = ['airfryer', 'oven', 'stove', 'blender/mixer', 'microwave', 'slow-cooker'];
const DIETARY_OPTIONS = ['gluten-free', 'lactose-free', 'vegetarian', 'vegan', 'low-carb', 'nut-free'];

function ProfileManager({ user, profile, isLoading, onProfileUpdate }) {
  const [newIngName, setNewIngName] = useState('');
  const [newIngQty, setNewIngQty] = useState(1);
  const [newIngUnit, setNewIngUnit] = useState('unit');
  
  const [isUpdating, setIsUpdating] = useState(false);

  const handleApplianceToggle = async (applianceName) => {
    setIsUpdating(true);
    const updated = profile.appliances.includes(applianceName)
      ? profile.appliances.filter(a => a !== applianceName)
      : [...profile.appliances, applianceName];
    
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/appliances`, {
        appliances: updated
      });
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleRestrictionToggle = async (restrictionName) => {
    setIsUpdating(true);
    const updated = profile.restrictions.includes(restrictionName)
      ? profile.restrictions.filter(r => r !== restrictionName)
      : [...profile.restrictions, restrictionName];
      
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/restrictions`, {
        restrictions: updated
      });
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddIngredient = async (e) => {
    e.preventDefault();
    if (!newIngName.trim()) return;
    setIsUpdating(true);

    const newItem = {
      name: newIngName.trim().lowerCase || newIngName.trim().toLowerCase(),
      quantity: parseFloat(newIngQty) || 1.0,
      unit: newIngUnit.trim().toLowerCase()
    };

    // Check if ingredient exists, add to it, or append
    const existsIndex = profile.ingredients.findIndex(i => i.name.toLowerCase() === newItem.name);
    let updated;
    if (existsIndex >= 0) {
      updated = [...profile.ingredients];
      updated[existsIndex].quantity += newItem.quantity;
    } else {
      updated = [...profile.ingredients, newItem];
    }

    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/ingredients`, {
        ingredients: updated
      });
      setNewIngName('');
      setNewIngQty(1);
      setNewIngUnit('unit');
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleRemoveIngredient = async (ingName) => {
    setIsUpdating(true);
    const updated = profile.ingredients.filter(i => i.name !== ingName);
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/ingredients`, {
        ingredients: updated
      });
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleClearMemory = async () => {
    if (!window.confirm("Are you sure you want to clear AI's short and long-term memory about you? This deletes all extracted facts and chat history.")) return;
    setIsUpdating(true);
    try {
      await axios.delete(`${API_BASE}/api/users/${user.user_id}/facts`);
      await axios.delete(`${API_BASE}/api/users/${user.user_id}/chat-history`);
      onProfileUpdate();
      alert("AI Memory cleared successfully! Ready for a clean slate.");
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="dashboard-grid">
      {/* Sidebar: Configuration (Appliances, Restrictions, AI memory) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Appliances Panel */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-display)', marginBottom: '1rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '0.5rem' }}>
            My Kitchen Appliances
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {APPLIANCE_OPTIONS.map(appOption => {
              const active = profile.appliances.includes(appOption);
              return (
                <button
                  key={appOption}
                  type="button"
                  className="btn-secondary"
                  disabled={isUpdating}
                  onClick={() => handleApplianceToggle(appOption)}
                  style={{
                    fontSize: '0.85rem',
                    padding: '0.4rem 0.8rem',
                    borderRadius: '8px',
                    borderColor: active ? 'hsl(var(--primary))' : 'hsl(var(--border))',
                    background: active ? 'rgba(16, 185, 129, 0.12)' : '',
                    color: active ? '#fff' : 'hsl(var(--text-secondary))'
                  }}
                >
                  {appOption}
                </button>
              );
            })}
          </div>
        </div>

        {/* Dietary Restrictions Panel */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-display)', marginBottom: '1rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '0.5rem' }}>
            Dietary Restrictions
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {DIETARY_OPTIONS.map(dietOption => {
              const active = profile.restrictions.includes(dietOption);
              return (
                <button
                  key={dietOption}
                  type="button"
                  className="btn-secondary"
                  disabled={isUpdating}
                  onClick={() => handleRestrictionToggle(dietOption)}
                  style={{
                    fontSize: '0.85rem',
                    padding: '0.4rem 0.8rem',
                    borderRadius: '8px',
                    borderColor: active ? 'hsl(var(--danger))' : 'hsl(var(--border))',
                    background: active ? 'rgba(244, 63, 94, 0.12)' : '',
                    color: active ? '#fff' : 'hsl(var(--text-secondary))'
                  }}
                >
                  {dietOption}
                </button>
              );
            })}
          </div>
        </div>

        {/* AI Memory Panel */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '0.5rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Sparkles size={16} style={{ color: 'hsl(var(--secondary))' }} />
              AI Long-Term Memory
            </h2>
            {profile.facts.length > 0 && (
              <button 
                onClick={handleClearMemory}
                style={{ fontSize: '0.75rem', background: 'transparent', color: 'hsl(var(--danger))', textDecoration: 'underline' }}
                disabled={isUpdating}
              >
                Clear
              </button>
            )}
          </div>
          
          <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }} className="custom-scroll">
            {profile.facts.length === 0 ? (
              <div className="empty-state" style={{ padding: '0.5rem' }}>
                No facts saved yet. Chat with the assistant, and it will extract facts automatically!
              </div>
            ) : (
              profile.facts.map((fact, index) => (
                <div key={index} style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', background: 'rgba(255, 255, 255, 0.01)', padding: '0.4rem 0.6rem', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}>
                  <Sparkles size={12} style={{ color: 'hsl(var(--primary))', marginTop: '0.15rem', flexShrink: 0 }} />
                  <span>{fact}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area: Ingredients Inventory */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignBars: 'center', marginBottom: '1.5rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-display)', fontWeight: '700' }}>Kitchen Ingredients Inventory</h1>
            <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Manage what you have in stock. The AI uses this list to recommend recipes.
            </p>
          </div>
          {(isLoading || isUpdating) && (
            <div style={{ color: 'hsl(var(--primary))', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <RefreshCw size={14} className="pulse" />
              <span>Saving...</span>
            </div>
          )}
        </div>

        {/* Add Ingredient Form */}
        <form onSubmit={handleAddIngredient} style={{ display: 'grid', gridTemplateColumns: '1fr 100px 100px auto', gap: '0.75rem', alignItems: 'end', marginBottom: '1.5rem', background: 'rgba(255, 255, 255, 0.01)', padding: '1rem', border: '1px dashed hsl(var(--border))', borderRadius: '10px' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Ingredient Name</label>
            <input 
              type="text" 
              className="form-input" 
              placeholder="e.g. olive oil"
              value={newIngName}
              onChange={(e) => setNewIngName(e.target.value)}
              disabled={isUpdating}
              required
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Qty</label>
            <input 
              type="number" 
              step="any"
              min="0.01"
              className="form-input" 
              value={newIngQty}
              onChange={(e) => setNewIngQty(e.target.value)}
              disabled={isUpdating}
              required
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Unit</label>
            <input 
              type="text" 
              className="form-input" 
              placeholder="e.g. ml, g, unit"
              value={newIngUnit}
              onChange={(e) => setNewIngUnit(e.target.value)}
              disabled={isUpdating}
              required
            />
          </div>
          <button type="submit" className="btn-primary" style={{ padding: '0.75rem 1.25rem' }} disabled={isUpdating}>
            <Plus size={18} />
            <span>Add</span>
          </button>
        </form>

        {/* Ingredients List */}
        <div style={{ flexGrow: 1 }} className="custom-scroll">
          {profile.ingredients.length === 0 ? (
            <div className="empty-state" style={{ padding: '3rem 0' }}>
              <AlertCircle size={32} style={{ color: 'hsl(var(--text-muted))', marginBottom: '0.5rem' }} />
              <p>Your kitchen pantry is empty!</p>
              <p style={{ fontSize: '0.8rem' }}>Add some ingredients above, upload a shopping receipt, or chat with the AI.</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.75rem' }}>
              {profile.ingredients.map(ing => (
                <div 
                  key={ing.name} 
                  style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    padding: '0.75rem 1rem', 
                    background: 'rgba(255, 255, 255, 0.02)', 
                    border: '1px solid hsl(var(--border))', 
                    borderRadius: '10px',
                    transition: 'var(--transition-fast)'
                  }}
                  className="inventory-card"
                >
                  <div>
                    <div style={{ fontWeight: '600', textTransform: 'capitalize' }}>{ing.name}</div>
                    <div style={{ fontSize: '0.8rem', color: 'hsl(var(--text-secondary))', marginTop: '0.15rem' }}>
                      Quantity: <strong style={{ color: 'hsl(var(--primary))' }}>{ing.quantity}</strong> {ing.unit}
                    </div>
                  </div>
                  <button 
                    type="button" 
                    onClick={() => handleRemoveIngredient(ing.name)}
                    style={{ background: 'transparent', color: 'hsl(var(--text-muted))', padding: '0.25rem' }}
                    className="delete-ing-btn"
                    disabled={isUpdating}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProfileManager;
