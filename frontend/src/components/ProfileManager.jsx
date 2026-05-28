import { useState, useEffect } from 'react';
import axios from 'axios';
import { Trash2, Plus, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { getIngredientCategory, CATEGORY_STYLES } from '../utils/ingredientCategories';

const API_BASE = 'http://localhost:8000';

const APPLIANCE_OPTIONS = ['airfryer', 'oven', 'stove', 'blender/mixer', 'microwave', 'slow-cooker'];
const DIETARY_OPTIONS = ['gluten-free', 'lactose-free', 'vegetarian', 'vegan', 'low-carb', 'nut-free'];

function ProfileManager({ user, profile, isLoading, onProfileUpdate }) {
  const [newIngName, setNewIngName] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [activeRestrictionModal, setActiveRestrictionModal] = useState(null);
  const [confirmModal, setConfirmModal] = useState(null);

  // Load temporary disabled restrictions state
  const [tempDisabledRestrictions, setTempDisabledRestrictions] = useState(() => {
    try {
      const stored = localStorage.getItem(`temp_disabled_restrictions_${user.user_id}`);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  // Current time state to avoid calling Date.now() during render (react-hooks/purity rule)
  const [currentTime, setCurrentTime] = useState(() => Date.now());

  // Combined timer effect for ticks and expiration checks
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      setCurrentTime(now);

      if (!user?.user_id || !profile?.restrictions) return;

      const expiredList = [];
      const updatedTemp = { ...tempDisabledRestrictions };
      let changed = false;

      Object.entries(tempDisabledRestrictions).forEach(([restName, expTime]) => {
        if (expTime <= now) {
          expiredList.push(restName);
          delete updatedTemp[restName];
          changed = true;
        }
      });

      if (changed) {
        setTempDisabledRestrictions(updatedTemp);
        localStorage.setItem(`temp_disabled_restrictions_${user.user_id}`, JSON.stringify(updatedTemp));

        const reactivate = async () => {
          const newRestrictions = [...profile.restrictions];
          let dbChanged = false;

          expiredList.forEach(rest => {
            if (!newRestrictions.includes(rest)) {
              newRestrictions.push(rest);
              dbChanged = true;
            }
          });

          if (dbChanged) {
            try {
              await axios.post(`${API_BASE}/api/users/${user.user_id}/restrictions`, {
                restrictions: newRestrictions
              });
              onProfileUpdate();
            } catch (err) {
              console.error("Error auto-reactivating restriction:", err);
            }
          }
        };

        reactivate();
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [user?.user_id, profile?.restrictions, tempDisabledRestrictions, onProfileUpdate]);

  // Sync state from localStorage when profile restrictions change (e.g. from Clear History in Chat)
  useEffect(() => {
    try {
      const stored = localStorage.getItem(`temp_disabled_restrictions_${user.user_id}`);
      const parsed = stored ? JSON.parse(stored) : {};
      Promise.resolve().then(() => {
        setTempDisabledRestrictions(parsed);
      });
    } catch {
      Promise.resolve().then(() => {
        setTempDisabledRestrictions({});
      });
    }
  }, [profile.restrictions, user.user_id]);

  const handleApplianceToggle = (applianceName) => {
    const isCurrentlyActive = profile.appliances.includes(applianceName);
    setConfirmModal({
      type: 'appliance',
      name: applianceName,
      action: isCurrentlyActive ? 'remove' : 'add',
      onConfirm: () => executeApplianceToggle(applianceName, isCurrentlyActive)
    });
  };

  const executeApplianceToggle = async (applianceName, isCurrentlyActive) => {
    setConfirmModal(null);
    setIsUpdating(true);
    const updated = isCurrentlyActive
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
    const isActive = profile.restrictions.includes(restrictionName);
    const isTempDisabled = tempDisabledRestrictions[restrictionName] && tempDisabledRestrictions[restrictionName] > currentTime;

    if (isTempDisabled) {
      // Reactivate immediately (re-add to DB, remove from temp list)
      setIsUpdating(true);
      const updatedTemp = { ...tempDisabledRestrictions };
      delete updatedTemp[restrictionName];
      setTempDisabledRestrictions(updatedTemp);
      localStorage.setItem(`temp_disabled_restrictions_${user.user_id}`, JSON.stringify(updatedTemp));

      const updated = [...profile.restrictions, restrictionName];
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
      return;
    }

    if (isActive) {
      // Open custom options modal for active restriction
      setActiveRestrictionModal(restrictionName);
    } else {
      // Inactive: confirm adding it
      setConfirmModal({
        type: 'restriction',
        name: restrictionName,
        action: 'add',
        onConfirm: () => executeAddRestriction(restrictionName)
      });
    }
  };

  const executeAddRestriction = async (restrictionName) => {
    setConfirmModal(null);
    setIsUpdating(true);
    const updated = [...profile.restrictions, restrictionName];
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

  const handleTempDisable = async (restrictionName) => {
    setIsUpdating(true);
    setActiveRestrictionModal(null);

    const expirationTime = Date.now() + 30 * 60 * 1000;
    const updatedTemp = {
      ...tempDisabledRestrictions,
      [restrictionName]: expirationTime
    };
    setTempDisabledRestrictions(updatedTemp);
    localStorage.setItem(`temp_disabled_restrictions_${user.user_id}`, JSON.stringify(updatedTemp));

    const updated = profile.restrictions.filter(r => r !== restrictionName);
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

  const handlePermanentRemove = async (restrictionName) => {
    setIsUpdating(true);
    setActiveRestrictionModal(null);

    const updatedTemp = { ...tempDisabledRestrictions };
    delete updatedTemp[restrictionName];
    setTempDisabledRestrictions(updatedTemp);
    localStorage.setItem(`temp_disabled_restrictions_${user.user_id}`, JSON.stringify(updatedTemp));

    const updated = profile.restrictions.filter(r => r !== restrictionName);
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

  const getRemainingTimeStr = (expirationTime) => {
    const diff = expirationTime - currentTime;
    if (diff <= 0) return '';
    const mins = Math.floor(diff / 60000);
    const secs = Math.floor((diff % 60000) / 1000);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleAddIngredient = async (e) => {
    e.preventDefault();
    if (!newIngName.trim()) return;
    setIsUpdating(true);

    const name = newIngName.trim().toLowerCase();

    // Check if ingredient exists, otherwise append
    let updated;
    if (profile.ingredients.includes(name)) {
      updated = [...profile.ingredients];
    } else {
      updated = [...profile.ingredients, name];
    }

    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/ingredients`, {
        ingredients: updated
      });
      setNewIngName('');
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleRemoveIngredient = async (ingName) => {
    setIsUpdating(true);
    const updated = profile.ingredients.filter(name => name !== ingName);
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

  const handleFillAllKb = async () => {
    if (!window.confirm("Would you like to populate your kitchen inventory with all ingredients from the dictionary? Existing ingredients will be preserved.")) return;
    setIsUpdating(true);
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/ingredients/add-all-kb`);
      onProfileUpdate();
    } catch (err) {
      console.error("Error filling ingredients dictionary:", err);
      alert("Failed to fill ingredients from the dictionary.");
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



  const wantsList = profile.wants_temporary
    ? profile.wants_temporary.split(',').map(w => w.trim()).filter(Boolean)
    : [];

  const notWantsList = profile.does_not_want_temporary
    ? profile.does_not_want_temporary.split(',').map(nw => nw.trim()).filter(Boolean)
    : [];

  const handleDeleteWant = async (wantToRemove) => {
    setIsUpdating(true);
    const updatedWants = wantsList.filter(w => w !== wantToRemove).join(', ');
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/temporary-preferences`, {
        wants_temporary: updatedWants,
        does_not_want_temporary: profile.does_not_want_temporary || ""
      });
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDeleteDislike = async (dislikeToRemove) => {
    setIsUpdating(true);
    const updatedNotWants = notWantsList.filter(nw => nw !== dislikeToRemove).join(', ');
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/temporary-preferences`, {
        wants_temporary: profile.wants_temporary || "",
        does_not_want_temporary: updatedNotWants
      });
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleClearWants = async () => {
    if (!window.confirm("Are you sure you want to clear all temporary wants?")) return;
    setIsUpdating(true);
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/temporary-preferences`, {
        wants_temporary: "",
        does_not_want_temporary: profile.does_not_want_temporary || ""
      });
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleClearDislikes = async () => {
    if (!window.confirm("Are you sure you want to clear all temporary dislikes?")) return;
    setIsUpdating(true);
    try {
      await axios.post(`${API_BASE}/api/users/${user.user_id}/temporary-preferences`, {
        wants_temporary: profile.wants_temporary || "",
        does_not_want_temporary: ""
      });
      onProfileUpdate();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  // Group user's ingredients by category
  const categorizedIngredients = {};
  profile.ingredients.forEach(ing => {
    const cat = getIngredientCategory(ing);
    if (!categorizedIngredients[cat]) {
      categorizedIngredients[cat] = [];
    }
    categorizedIngredients[cat].push(ing);
  });

  const categoryOrder = [
    'Meat, Poultry & Seafood',
    'Fruits',
    'Vegetables & Greens',
    'Dairy & Eggs',
    'Grains, Pasta & Baking',
    'Oils, Condiments & Liquids',
    'Herbs, Spices & Seasonings',
    'Other Pantry Items'
  ];

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
              const expTime = tempDisabledRestrictions[dietOption];
              const isTempDisabled = expTime && expTime > currentTime;

              let borderStyle = 'solid';
              let borderColor = 'hsl(var(--border))';
              let background = '';
              let color = 'hsl(var(--text-secondary))';
              let label = dietOption;

              if (active) {
                borderColor = 'hsl(var(--danger))';
                background = 'rgba(244, 63, 94, 0.12)';
                color = '#fff';
              } else if (isTempDisabled) {
                borderStyle = 'dashed';
                borderColor = '#f59e0b';
                background = 'rgba(245, 158, 11, 0.08)';
                color = '#fcd34d';
                label = `${dietOption} (Paused: ${getRemainingTimeStr(expTime)})`;
              }

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
                    borderStyle,
                    borderColor,
                    background,
                    color
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* AI Long-Term Memory Panel */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '0.5rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Sparkles size={16} style={{ color: 'hsl(var(--secondary))' }} />
              Long-Term Memory
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

        {/* AI Short-Term Memory Panel (Wants) */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '0.5rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Sparkles size={16} style={{ color: 'hsl(var(--primary))' }} />
              Short-Term Wants (Temporary)
            </h2>
            {wantsList.length > 0 && (
              <button 
                onClick={handleClearWants}
                style={{ fontSize: '0.75rem', background: 'transparent', color: 'hsl(var(--danger))', textDecoration: 'underline' }}
                disabled={isUpdating}
              >
                Clear
              </button>
            )}
          </div>
          
          <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }} className="custom-scroll">
            {wantsList.length === 0 ? (
              <div className="empty-state" style={{ padding: '0.5rem' }}>
                No temporary wants saved yet (e.g. "pasta", "spicy", "anything").
              </div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {wantsList.map((want, index) => (
                  <span 
                    key={index} 
                    style={{ 
                      display: 'inline-flex', 
                      alignItems: 'center', 
                      gap: '0.25rem', 
                      fontSize: '0.8rem', 
                      color: 'hsl(var(--primary))', 
                      background: 'rgba(16, 185, 129, 0.08)', 
                      border: '1px solid rgba(16, 185, 129, 0.2)', 
                      padding: '0.25rem 0.5rem', 
                      borderRadius: '6px' 
                    }}
                  >
                    <span>{want}</span>
                    <button 
                      type="button" 
                      onClick={() => handleDeleteWant(want)} 
                      disabled={isUpdating}
                      style={{ 
                        background: 'transparent', 
                        border: 'none', 
                        cursor: 'pointer', 
                        display: 'flex', 
                        alignItems: 'center', 
                        padding: '0.1rem', 
                        color: 'hsl(var(--text-muted))',
                        transition: 'color 0.2s'
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* AI Short-Term Memory Panel (Dislikes) */}
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '0.5rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Sparkles size={16} style={{ color: 'hsl(var(--danger))' }} />
              Short-Term Dislikes (Temporary)
            </h2>
            {notWantsList.length > 0 && (
              <button 
                onClick={handleClearDislikes}
                style={{ fontSize: '0.75rem', background: 'transparent', color: 'hsl(var(--danger))', textDecoration: 'underline' }}
                disabled={isUpdating}
              >
                Clear
              </button>
            )}
          </div>
          
          <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }} className="custom-scroll">
            {notWantsList.length === 0 ? (
              <div className="empty-state" style={{ padding: '0.5rem' }}>
                No temporary dislikes saved yet (e.g. "onions", "cheese").
              </div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {notWantsList.map((dislike, index) => (
                  <span 
                    key={index} 
                    style={{ 
                      display: 'inline-flex', 
                      alignItems: 'center', 
                      gap: '0.25rem', 
                      fontSize: '0.8rem', 
                      color: 'hsl(var(--danger))', 
                      background: 'rgba(244, 63, 94, 0.08)', 
                      border: '1px solid rgba(244, 63, 94, 0.2)', 
                      padding: '0.25rem 0.5rem', 
                      borderRadius: '6px' 
                    }}
                  >
                    <span>{dislike}</span>
                    <button 
                      type="button" 
                      onClick={() => handleDeleteDislike(dislike)} 
                      disabled={isUpdating}
                      style={{ 
                        background: 'transparent', 
                        border: 'none', 
                        cursor: 'pointer', 
                        display: 'flex', 
                        alignItems: 'center', 
                        padding: '0.1rem', 
                        color: 'hsl(var(--text-muted))',
                        transition: 'color 0.2s'
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area: Ingredients Inventory */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-display)', fontWeight: '700' }}>Kitchen Ingredients Inventory</h1>
            <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Manage what you have in stock. The AI uses this list to recommend recipes.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button 
              type="button"
              onClick={handleFillAllKb}
              className="btn-secondary"
              disabled={isUpdating || isLoading}
              style={{
                fontSize: '0.85rem',
                padding: '0.5rem 0.85rem',
                borderRadius: '8px',
                borderColor: 'hsl(var(--primary))',
                background: 'rgba(16, 185, 129, 0.05)',
                color: 'hsl(var(--primary))',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(16, 185, 129, 0.15)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(16, 185, 129, 0.05)';
                e.currentTarget.style.transform = 'none';
              }}
            >
              <Sparkles size={14} />
              <span>Fill Dictionary</span>
            </button>
            {(isLoading || isUpdating) && (
              <div style={{ color: 'hsl(var(--primary))', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                <RefreshCw size={14} className="pulse" />
                <span>Saving...</span>
              </div>
            )}
          </div>
        </div>

        {/* Add Ingredient Form */}
        <form onSubmit={handleAddIngredient} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.75rem', alignItems: 'end', marginBottom: '1.5rem', background: 'rgba(255, 255, 255, 0.01)', padding: '1rem', border: '1px dashed hsl(var(--border))', borderRadius: '10px' }}>
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {categoryOrder.map(catKey => {
                const items = categorizedIngredients[catKey] || [];
                if (items.length === 0) return null;
                const catStyle = CATEGORY_STYLES[catKey] || CATEGORY_STYLES['Other Pantry Items'];
                
                return (
                  <div 
                    key={catKey} 
                    style={{ 
                      background: 'rgba(255, 255, 255, 0.01)', 
                      border: '1px solid hsl(var(--border))', 
                      borderLeft: `4px solid ${catStyle.accent}`, 
                      borderRadius: '12px', 
                      padding: '1.25rem',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                    }}
                  >
                    <h3 style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      fontSize: '1.05rem', 
                      fontWeight: '700', 
                      color: '#fff', 
                      marginBottom: '1rem', 
                      fontFamily: 'var(--font-display)' 
                    }}>
                      <span style={{ marginRight: '0.5rem', fontSize: '1.25rem' }}>{catStyle.emoji}</span>
                      {catKey}
                      <span style={{
                        fontSize: '0.75rem',
                        padding: '0.2rem 0.6rem',
                        borderRadius: '9999px',
                        background: catStyle.pillBg,
                        color: catStyle.text,
                        border: `1px solid ${catStyle.border}`,
                        fontWeight: '700',
                        marginLeft: '0.75rem',
                        display: 'inline-flex',
                        alignItems: 'center'
                      }}>{items.length}</span>
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
                      {items.map(ing => (
                        <div 
                          key={ing} 
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
                            <div style={{ fontWeight: '600', textTransform: 'capitalize', fontSize: '0.875rem' }}>{ing}</div>
                          </div>
                          <button 
                            type="button" 
                            onClick={() => handleRemoveIngredient(ing)}
                            style={{ background: 'transparent', color: 'hsl(var(--text-muted))', padding: '0.25rem' }}
                            className="delete-ing-btn"
                            disabled={isUpdating}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>

      {/* Custom Modal for dietary restriction adjustment */}
      {activeRestrictionModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            background: 'hsl(var(--bg-card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '16px',
            padding: '1.75rem',
            maxWidth: '440px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem'
          }}>
            <div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '700', fontFamily: 'var(--font-display)', color: '#fff', display: 'flex', alignItems: 'center', gap: '0.5rem', textTransform: 'capitalize' }}>
                🛡️ Manage {activeRestrictionModal}
              </h3>
              <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem', marginTop: '0.5rem', lineHeight: '1.5' }}>
                Would you like to temporarily disable the <strong>{activeRestrictionModal}</strong> restriction for 30 minutes to explore other recipes, or remove it permanently from your profile?
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button 
                type="button" 
                className="btn-primary" 
                onClick={() => handleTempDisable(activeRestrictionModal)}
                style={{ 
                  background: 'linear-gradient(90deg, #d97706, #f59e0b)',
                  border: 'none',
                  color: '#fff',
                  padding: '0.65rem',
                  fontWeight: '600'
                }}
              >
                ⏱️ Temporarily Disable for 30 Mins
              </button>
              
              <button 
                type="button" 
                className="btn-danger" 
                onClick={() => handlePermanentRemove(activeRestrictionModal)}
                style={{ 
                  padding: '0.65rem',
                  fontWeight: '600'
                }}
              >
                🗑️ Permanently Remove Restriction
              </button>

              <button 
                type="button" 
                className="btn-secondary" 
                onClick={() => setActiveRestrictionModal(null)}
                style={{ 
                  padding: '0.65rem',
                  marginTop: '0.25rem'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(3px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            background: 'hsl(var(--bg-card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '16px',
            padding: '1.5rem',
            maxWidth: '400px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
            animation: 'slideUp 0.2s ease-out'
          }}>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{
                background: confirmModal.action === 'add' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                color: confirmModal.action === 'add' ? 'hsl(var(--primary))' : 'hsl(var(--danger))',
                borderRadius: '50%',
                padding: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                {confirmModal.action === 'add' ? (
                  <Plus size={20} />
                ) : (
                  <Trash2 size={20} />
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: '700', fontFamily: 'var(--font-display)', color: '#fff' }}>
                  {confirmModal.action === 'add' ? 'Add' : 'Remove'} {confirmModal.type === 'appliance' ? 'Appliance' : 'Dietary Restriction'}?
                </h3>
                <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.875rem', lineHeight: '1.5', marginTop: '0.25rem' }}>
                  {confirmModal.type === 'appliance' ? (
                    confirmModal.action === 'add' ? (
                      <>Are you sure you want to add <strong>{confirmModal.name}</strong> to your kitchen appliances?</>
                    ) : (
                      <>Are you sure you want to remove <strong>{confirmModal.name}</strong> from your kitchen appliances?</>
                    )
                  ) : (
                    <>Are you sure you want to add the dietary restriction <strong>{confirmModal.name}</strong> to your profile?</>
                  )}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={() => setConfirmModal(null)}
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                disabled={isUpdating}
              >
                Cancel
              </button>
              <button 
                type="button" 
                className="btn-primary" 
                onClick={confirmModal.onConfirm}
                style={{ 
                  padding: '0.5rem 1.25rem', 
                  fontSize: '0.875rem',
                  background: confirmModal.action === 'add' 
                    ? 'linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary-hover)) 100%)' 
                    : 'linear-gradient(135deg, hsl(var(--danger)) 0%, #be123c 100%)',
                  color: confirmModal.action === 'add' ? '#0c111d' : '#fff',
                  border: 'none',
                  boxShadow: confirmModal.action === 'add' 
                    ? '0 4px 10px hsla(var(--primary) / 0.2)' 
                    : '0 4px 10px hsla(var(--danger) / 0.2)'
                }}
                disabled={isUpdating}
              >
                {confirmModal.action === 'add' ? 'Confirm Add' : 'Confirm Remove'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfileManager;
