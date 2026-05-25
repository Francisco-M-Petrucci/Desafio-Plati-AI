import React, { useState } from 'react';
import axios from 'axios';
import { ChefHat, Plus, Minus, Loader2, Check, ChevronRight, ChevronLeft, User, Lock, Sparkles, AlertCircle, ShoppingBag } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const APPLIANCE_OPTIONS = [
  { name: 'oven', label: 'Oven', emoji: '🍳', desc: 'For baking and roasting' },
  { name: 'stove', label: 'Stove', emoji: '🔥', desc: 'For boiling, pan frying and searing' },
  { name: 'airfryer', label: 'Airfryer', emoji: '🌬️', desc: 'For quick crispy healthy cooking' },
  { name: 'blender/mixer', label: 'Blender / Mixer', emoji: '🌪️', desc: 'For blending and mixing' },
  { name: 'microwave', label: 'Microwave', emoji: '⚡', desc: 'For reheating and quick melting' },
  { name: 'slow-cooker', label: 'Slow Cooker', emoji: '🍲', desc: 'For long low-temp stews' }
];

const DIETARY_OPTIONS = [
  { name: 'gluten-free', label: 'Gluten-Free', emoji: '🌾🚫', desc: 'No wheat, barley, or rye' },
  { name: 'lactose-free', label: 'Lactose-Free', emoji: '🥛🚫', desc: 'No dairy milk sugar' },
  { name: 'vegetarian', label: 'Vegetarian', emoji: '🥗', desc: 'No meat, poultry, or fish' },
  { name: 'vegan', label: 'Vegan', emoji: '🌱', desc: 'No animal products whatsoever' },
  { name: 'low-carb', label: 'Low-Carb', emoji: '🥩🥑', desc: 'Reduced carbohydrates intake' },
  { name: 'nut-free', label: 'Nut-Free', emoji: '🥜🚫', desc: 'Safe for nut allergy sufferers' }
];

const COMMON_INGREDIENTS = [
  { name: 'chicken wings', category: 'Proteins', emoji: '🍗', defaultUnit: 'kg', defaultQty: 1.0 },
  { name: 'chicken breast', category: 'Proteins', emoji: '🥩', defaultUnit: 'g', defaultQty: 500 },
  { name: 'salmon fillets', category: 'Proteins', emoji: '🐟', defaultUnit: 'g', defaultQty: 300 },
  { name: 'eggs', category: 'Proteins', emoji: '🥚', defaultUnit: 'unit', defaultQty: 6 },
  { name: 'extra-firm tofu', category: 'Proteins', emoji: '⬜', defaultUnit: 'g', defaultQty: 250 },
  { name: 'shrimp', category: 'Proteins', emoji: '🍤', defaultUnit: 'g', defaultQty: 300 },
  { name: 'tomato', category: 'Vegetables', emoji: '🍅', defaultUnit: 'unit', defaultQty: 3 },
  { name: 'onion', category: 'Vegetables', emoji: '🧅', defaultUnit: 'unit', defaultQty: 2 },
  { name: 'garlic', category: 'Vegetables', emoji: '🧄', defaultUnit: 'unit', defaultQty: 1 },
  { name: 'potatoes', category: 'Vegetables', emoji: '🥔', defaultUnit: 'unit', defaultQty: 4 },
  { name: 'carrots', category: 'Vegetables', emoji: '🥕', defaultUnit: 'unit', defaultQty: 3 },
  { name: 'cucumber', category: 'Vegetables', emoji: '🥒', defaultUnit: 'unit', defaultQty: 1 },
  { name: 'broccoli florets', category: 'Vegetables', emoji: '🥦', defaultUnit: 'g', defaultQty: 200 },
  { name: 'spinach', category: 'Vegetables', emoji: '🥬', defaultUnit: 'g', defaultQty: 100 },
  { name: 'lemon', category: 'Vegetables', emoji: '🍋', defaultUnit: 'unit', defaultQty: 2 },
  { name: 'avocado', category: 'Vegetables', emoji: '🥑', defaultUnit: 'unit', defaultQty: 2 },
  { name: 'mixed mushrooms', category: 'Vegetables', emoji: '🍄', defaultUnit: 'g', defaultQty: 200 },
  { name: 'fresh basil leaves', category: 'Herbs', emoji: '🌿', defaultUnit: 'bunch', defaultQty: 1 },
  { name: 'fresh mint leaves', category: 'Herbs', emoji: '🌿', defaultUnit: 'bunch', defaultQty: 1 },
  { name: 'cilantro', category: 'Herbs', emoji: '🌿', defaultUnit: 'bunch', defaultQty: 1 },
  { name: 'parsley', category: 'Herbs', emoji: '🌿', defaultUnit: 'bunch', defaultQty: 1 },
  { name: 'butter', category: 'Dairy', emoji: '🧈', defaultUnit: 'g', defaultQty: 200 },
  { name: 'milk', category: 'Dairy', emoji: '🥛', defaultUnit: 'ml', defaultQty: 1000 },
  { name: 'heavy cream', category: 'Dairy', emoji: '🥛', defaultUnit: 'ml', defaultQty: 200 },
  { name: 'parmesan cheese', category: 'Dairy', emoji: '🧀', defaultUnit: 'g', defaultQty: 100 },
  { name: 'fresh mozzarella cheese', category: 'Dairy', emoji: '🧀', defaultUnit: 'g', defaultQty: 250 },
  { name: 'feta cheese', category: 'Dairy', emoji: '🧀', defaultUnit: 'g', defaultQty: 150 },
  { name: 'olive oil', category: 'Pantry', emoji: '🫒', defaultUnit: 'ml', defaultQty: 500 },
  { name: 'vegetable broth', category: 'Pantry', emoji: '🥣', defaultUnit: 'ml', defaultQty: 1000 },
  { name: 'beef broth', category: 'Pantry', emoji: '🥣', defaultUnit: 'ml', defaultQty: 1000 },
  { name: 'soy sauce', category: 'Pantry', emoji: '🏺', defaultUnit: 'ml', defaultQty: 150 },
  { name: 'canned tomatoes', category: 'Pantry', emoji: '🥫', defaultUnit: 'can', defaultQty: 1 },
  { name: 'penne pasta', category: 'Grains', emoji: '🍝', defaultUnit: 'g', defaultQty: 500 },
  { name: 'arborio rice', category: 'Grains', emoji: '🍚', defaultUnit: 'g', defaultQty: 500 },
  { name: 'pizza dough', category: 'Grains', emoji: '🍞', defaultUnit: 'unit', defaultQty: 1 },
  { name: 'all-purpose flour', category: 'Baking', emoji: '🌾', defaultUnit: 'g', defaultQty: 1000 },
  { name: 'sugar', category: 'Baking', emoji: '🍬', defaultUnit: 'g', defaultQty: 500 },
  { name: 'chocolate chips', category: 'Baking', emoji: '🍫', defaultUnit: 'g', defaultQty: 200 },
  { name: 'ripe bananas', category: 'Fruits', emoji: '🍌', defaultUnit: 'unit', defaultQty: 3 },
  { name: 'watermelon cubes', category: 'Fruits', emoji: '🍉', defaultUnit: 'g', defaultQty: 500 }
];

function RegisterWizard({ onRegisterSuccess, onCancel }) {
  const [step, setStep] = useState(1);
  const [credentials, setCredentials] = useState({ firstName: '', username: '', password: '' });
  const [selectedAppliances, setSelectedAppliances] = useState([]);
  const [selectedRestrictions, setSelectedRestrictions] = useState([]);
  const [selectedIngredients, setSelectedIngredients] = useState({}); // name -> { emoji }
  
  // Custom unlisted ingredient form states
  const [customIngName, setCustomIngName] = useState('');

  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadingTipIndex, setLoadingTipIndex] = useState(0);

  const loadingTips = [
    "Saving your kitchen preferences...",
    "Analyzing your cooking appliances...",
    "Formatting your dietary restrictions...",
    "Querying Chef RAG tool for 5 perfect initial recipes...",
    "Running ingredients similarity search matching your stock...",
    "Storing details in your private companion database...",
    "Almost ready! Finalizing your workspace..."
  ];

  // Rotate loading tips during register loading page
  React.useEffect(() => {
    let interval;
    if (isSubmitting) {
      interval = setInterval(() => {
        setLoadingTipIndex((prev) => (prev + 1) % loadingTips.length);
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [isSubmitting]);

  const handleCredentialsChange = (e) => {
    setCredentials({ ...credentials, [e.target.name]: e.target.value });
    setError('');
  };

  const nextStep = () => {
    if (step === 1) {
      if (!credentials.firstName.trim()) {
        setError('First Name is required');
        return;
      }
      if (!credentials.username.trim()) {
        setError('Username is required');
        return;
      }
      if (!credentials.password.trim()) {
        setError('Password is required');
        return;
      }
    }
    setError('');
    setStep(step + 1);
  };

  const prevStep = () => {
    setError('');
    setStep(step - 1);
  };

  const toggleAppliance = (app) => {
    setSelectedAppliances(prev =>
      prev.includes(app) ? prev.filter(a => a !== app) : [...prev, app]
    );
  };

  const toggleRestriction = (rest) => {
    setSelectedRestrictions(prev =>
      prev.includes(rest) ? prev.filter(r => r !== rest) : [...prev, rest]
    );
  };

  const handleIngredientToggle = (ing) => {
    setSelectedIngredients(prev => {
      const next = { ...prev };
      if (next[ing.name]) {
        delete next[ing.name];
      } else {
        next[ing.name] = {
          emoji: ing.emoji
        };
      }
      return next;
    });
  };

  const handleAddCustomIngredient = (e) => {
    e.preventDefault();
    const name = customIngName.trim().toLowerCase();
    if (!name) return;

    setSelectedIngredients(prev => ({
      ...prev,
      [name]: {
        emoji: '📦'
      }
    }));

    setCustomIngName('');
  };

  const handleRemoveSelectedIngredient = (name) => {
    setSelectedIngredients(prev => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError('');

    // Format selected ingredients into backend schema list
    const ingredientsList = Object.keys(selectedIngredients);

    const payload = {
      first_name: credentials.firstName.trim(),
      username: credentials.username.trim().toLowerCase(),
      password: credentials.password,
      appliances: selectedAppliances,
      restrictions: selectedRestrictions,
      ingredients: ingredientsList
    };

    try {
      const res = await axios.post(`${API_BASE}/api/auth/register`, payload);
      // Wait another 800ms to allow matching logic simulation transition nicely
      setTimeout(() => {
        onRegisterSuccess(res.data);
      }, 1000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Check if username is taken.');
      setIsSubmitting(false);
      setStep(1); // Go back to credentials screen if failed
    }
  };

  // --- RENDERS ---

  if (isSubmitting) {
    return (
      <div className="login-container">
        <div className="login-card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
          <div style={{ position: 'relative', display: 'inline-block', marginBottom: '2rem' }}>
            <div style={{ position: 'absolute', inset: 0, background: 'hsl(var(--primary))', filter: 'blur(20px)', opacity: 0.15, borderRadius: '50%' }}></div>
            <div style={{ padding: '1rem', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.15)', borderRadius: '50%', color: 'hsl(var(--primary))' }}>
              <Loader2 size={48} className="pulse" style={{ animation: 'spin 1.5s linear infinite' }} />
            </div>
          </div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: '800', marginBottom: '0.5rem', color: '#fff' }}>
            Please wait while we create your account
          </h2>
          <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem', minHeight: '3rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {loadingTips[loadingTipIndex]}
          </p>
          <div style={{ width: '100%', height: '4px', background: 'hsl(var(--border))', borderRadius: '2px', overflow: 'hidden', marginTop: '1rem' }}>
            <div style={{ width: '80%', height: '100%', background: 'linear-gradient(90deg, hsl(var(--primary)), hsl(var(--secondary)))', borderRadius: '2px', animation: 'pulse 1.5s ease-in-out infinite' }}></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container" style={{ padding: '2rem 1rem' }}>
      <div className="login-card" style={{ maxWidth: step === 4 ? '760px' : '520px', width: '100%', transition: 'all 0.3s ease' }}>
        
        {/* Progress & Header */}
        <div style={{ borderBottom: '1px solid hsl(var(--border))', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'hsl(var(--primary))' }}>
              <ChefHat size={22} />
              <span style={{ fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Create Profile</span>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'hsl(var(--text-muted))', fontWeight: '600' }}>
              Step {step} of 4
            </span>
          </div>
          
          <div style={{ display: 'flex', gap: '0.35rem', height: '3px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
            {[1, 2, 3, 4].map(s => (
              <div 
                key={s} 
                style={{ 
                  flexGrow: 1, 
                  background: s <= step ? 'linear-gradient(90deg, hsl(var(--primary)), hsl(var(--secondary)))' : 'transparent',
                  opacity: s <= step ? 1 : 0.2,
                  transition: 'background 0.3s ease'
                }}
              />
            ))}
          </div>

          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: '700', marginTop: '1rem', color: '#fff' }}>
            {step === 1 && "Account Information"}
            {step === 2 && "Kitchen Cooking Appliances"}
            {step === 3 && "Dietary Restrictions"}
            {step === 4 && "Select Available Ingredients"}
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'hsl(var(--text-secondary))', marginTop: '0.25rem' }}>
            {step === 1 && "Set up your credentials so you can log in later."}
            {step === 2 && "Select the cooking tools you have at home. Chef will only show recipes you can cook."}
            {step === 3 && "Select any allergies or dietary limitations. Chef will filter these ingredients out."}
            {step === 4 && "Check the ingredients you have in stock, then specify their quantities."}
          </p>
        </div>

        {error && (
          <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.2)', padding: '0.75rem', borderRadius: '8px', color: '#fda4af', fontSize: '0.85rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* STEP 1: CREDENTIALS */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="firstName">First Name</label>
              <div style={{ position: 'relative' }}>
                <input 
                  id="firstName"
                  name="firstName"
                  type="text" 
                  className="form-input" 
                  placeholder="e.g. Carol" 
                  value={credentials.firstName}
                  onChange={handleCredentialsChange}
                  style={{ paddingLeft: '2.5rem' }}
                />
                <User size={16} style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--text-muted))' }} />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="username">Username</label>
              <div style={{ position: 'relative' }}>
                <input 
                  id="username"
                  name="username"
                  type="text" 
                  className="form-input" 
                  placeholder="e.g. carol_cooks" 
                  value={credentials.username}
                  onChange={handleCredentialsChange}
                  style={{ paddingLeft: '2.5rem' }}
                />
                <User size={16} style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--text-muted))' }} />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">Password</label>
              <div style={{ position: 'relative' }}>
                <input 
                  id="password"
                  name="password"
                  type="password" 
                  className="form-input" 
                  placeholder="Create a secure password" 
                  value={credentials.password}
                  onChange={handleCredentialsChange}
                  style={{ paddingLeft: '2.5rem' }}
                />
                <Lock size={16} style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--text-muted))' }} />
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: APPLIANCES */}
        {step === 2 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            {APPLIANCE_OPTIONS.map(app => {
              const active = selectedAppliances.includes(app.name);
              return (
                <div 
                  key={app.name}
                  onClick={() => toggleAppliance(app.name)}
                  style={{
                    padding: '1rem',
                    border: '1px solid',
                    borderColor: active ? 'hsl(var(--primary))' : 'hsl(var(--border))',
                    background: active ? 'rgba(16, 185, 129, 0.04)' : 'rgba(255, 255, 255, 0.01)',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem',
                    position: 'relative'
                  }}
                  className="hover-card"
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '1.75rem' }}>{app.emoji}</span>
                    {active && (
                      <div style={{ background: 'hsl(var(--primary))', color: '#0c111d', borderRadius: '50%', padding: '0.15rem' }}>
                        <Check size={10} strokeWidth={3} />
                      </div>
                    )}
                  </div>
                  <strong style={{ fontSize: '0.9rem', color: '#fff', marginTop: '0.5rem' }}>{app.label}</strong>
                  <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-secondary))' }}>{app.desc}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* STEP 3: DIETARY RESTRICTIONS */}
        {step === 3 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            {DIETARY_OPTIONS.map(diet => {
              const active = selectedRestrictions.includes(diet.name);
              return (
                <div 
                  key={diet.name}
                  onClick={() => toggleRestriction(diet.name)}
                  style={{
                    padding: '1rem',
                    border: '1px solid',
                    borderColor: active ? 'hsl(var(--danger))' : 'hsl(var(--border))',
                    background: active ? 'rgba(244, 63, 94, 0.04)' : 'rgba(255, 255, 255, 0.01)',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem',
                    position: 'relative'
                  }}
                  className="hover-card"
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '1.75rem' }}>{diet.emoji}</span>
                    {active && (
                      <div style={{ background: 'hsl(var(--danger))', color: '#fff', borderRadius: '50%', padding: '0.15rem' }}>
                        <Check size={10} strokeWidth={3} />
                      </div>
                    )}
                  </div>
                  <strong style={{ fontSize: '0.9rem', color: '#fff', marginTop: '0.5rem' }}>{diet.label}</strong>
                  <span style={{ fontSize: '0.7rem', color: 'hsl(var(--text-secondary))' }}>{diet.desc}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* STEP 4: INGREDIENTS */}
        {step === 4 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Common Ingredients Catalog */}
            <div style={{ maxHeight: '280px', overflowY: 'auto', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem', paddingRight: '0.25rem' }} className="custom-scroll">
              {COMMON_INGREDIENTS.map(ing => {
                const isSelected = !!selectedIngredients[ing.name];
                
                return (
                  <div 
                    key={ing.name}
                    style={{
                      padding: '0.6rem 0.8rem',
                      border: '1px solid',
                      borderColor: isSelected ? 'hsl(var(--primary))' : 'hsl(var(--border))',
                      background: isSelected ? 'rgba(16, 185, 129, 0.03)' : 'rgba(255, 255, 255, 0.01)',
                      borderRadius: '10px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s ease',
                      cursor: 'pointer'
                    }}
                    onClick={() => handleIngredientToggle(ing)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>{ing.emoji}</span>
                      <div style={{ textAlign: 'left' }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: '600', textTransform: 'capitalize', color: isSelected ? '#fff' : 'hsl(var(--text-secondary))' }}>
                          {ing.name}
                        </div>
                      </div>
                    </div>

                    {isSelected && (
                      <div style={{ background: 'hsl(var(--primary))', color: '#0c111d', borderRadius: '50%', padding: '0.15rem' }}>
                        <Check size={10} strokeWidth={3} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Selected Ingredients List (Review Drawer) */}
            {Object.keys(selectedIngredients).length > 0 && (
              <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid hsl(var(--border))', borderRadius: '10px', padding: '1rem' }}>
                <h4 style={{ fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', color: 'hsl(var(--text-secondary))', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <ShoppingBag size={12} />
                  Your Selected Stock ({Object.keys(selectedIngredients).length})
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', maxHeight: '100px', overflowY: 'auto' }} className="custom-scroll">
                  {Object.entries(selectedIngredients).map(([name, item]) => (
                    <div 
                      key={name}
                      style={{ 
                        display: 'inline-flex', 
                        alignItems: 'center', 
                        gap: '0.35rem', 
                        fontSize: '0.75rem', 
                        padding: '0.25rem 0.5rem', 
                        background: 'rgba(255,255,255,0.04)', 
                        border: '1px solid hsl(var(--border))', 
                        borderRadius: '6px',
                        textTransform: 'capitalize'
                      }}
                    >
                      <span>{item.emoji} {name}</span>
                      
                      <button 
                        onClick={() => handleRemoveSelectedIngredient(name)}
                        style={{ color: 'hsl(var(--danger))', fontSize: '0.85rem', background: 'transparent', padding: '0.1rem' }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Custom Ingredient Submit Form */}
            <form onSubmit={handleAddCustomIngredient} style={{ borderTop: '1px dashed hsl(var(--border))', paddingTop: '1rem' }}>
              <h4 style={{ fontSize: '0.8rem', fontWeight: '600', color: 'hsl(var(--text-secondary))', marginBottom: '0.5rem', textAlign: 'left' }}>
                Can't find an ingredient? Add it here:
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.5rem', alignItems: 'end' }}>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="e.g. fresh oregano"
                  value={customIngName}
                  onChange={(e) => setCustomIngName(e.target.value)}
                  style={{ padding: '0.4rem 0.6rem', fontSize: '0.8rem' }}
                />
                <button type="submit" className="btn-secondary" style={{ padding: '0.45rem 0.8rem', borderRadius: '8px', fontSize: '0.8rem' }}>
                  <Plus size={14} />
                  <span>Add</span>
                </button>
              </div>
            </form>


          </div>
        )}

        {/* Navigations Buttons */}
        <div style={{ display: 'flex', justifyItems: 'center', justifyContent: 'space-between', borderTop: '1px solid hsl(var(--border))', paddingTop: '1.25rem', marginTop: '1.5rem', gap: '1rem' }}>
          {step > 1 ? (
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={prevStep}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
            >
              <ChevronLeft size={16} />
              <span>Back</span>
            </button>
          ) : (
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={onCancel}
            >
              Cancel
            </button>
          )}

          {step < 4 ? (
            <button 
              type="button" 
              className="btn-primary" 
              onClick={nextStep}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.6rem 1.25rem' }}
            >
              <span>Next</span>
              <ChevronRight size={16} />
            </button>
          ) : (
            <button 
              type="button" 
              className="btn-primary" 
              onClick={handleSubmit}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.6rem 1.5rem' }}
            >
              <Sparkles size={16} style={{ color: 'hsl(var(--secondary))' }} />
              <span>Finish Account Registration</span>
            </button>
          )}
        </div>

      </div>
    </div>
  );
}

export default RegisterWizard;
