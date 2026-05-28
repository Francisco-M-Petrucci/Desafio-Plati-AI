import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Clock, Check, X, ChevronRight, BookOpen, AlertTriangle } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const CULTURES = ['Mexican', 'Indian', 'Italian', 'American', 'Asian', 'French', 'Greek'];
const SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter'];

function RecipeBrowser({ user, profile }) {
  const [recipes, setRecipes] = useState([]);
  const [initialRecipes, setInitialRecipes] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedCulture, setSelectedCulture] = useState('');
  const [selectedSeason, setSelectedSeason] = useState('');
  
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [checkedSteps, setCheckedSteps] = useState({});

  useEffect(() => {
    fetchRecipes();
  }, [search, selectedCulture, selectedSeason]);

  useEffect(() => {
    if (user?.user_id) {
      fetchInitialRecipes();
    }
  }, [user]);

  const fetchRecipes = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/recipes`, {
        params: {
          query: search,
          culture: selectedCulture || undefined,
          season: selectedSeason || undefined
        }
      });
      setRecipes(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchInitialRecipes = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/users/${user.user_id}/initial-search`);
      setInitialRecipes(res.data);
    } catch (err) {
      console.error("Error fetching initial recipes:", err);
    }
  };

  const handleSelectRecipe = (recipe) => {
    setSelectedRecipe(recipe);
    setCheckedSteps({}); // Reset cooking checkmarks
  };

  const toggleStep = (index) => {
    setCheckedSteps(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  // Helper to determine if the user has a specific ingredient in their stock
  const checkIngredientMatch = (recipeIngName) => {
    const rName = recipeIngName.toLowerCase();
    
    // Perform loose match (e.g. if recipe says "chicken wings" and user has "chicken wings", or "garlic" vs "garlic powder")
    const match = profile.ingredients.find(uName => {
      const uNameLower = uName.toLowerCase();
      return rName.includes(uNameLower) || uNameLower.includes(rName);
    });

    return match ? { matched: true } : { matched: false };
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', width: '100%', margin: '0 auto', flexGrow: 1, display: 'grid', gridTemplateColumns: selectedRecipe ? '1fr 1fr' : '1fr', gap: '2rem' }}>
      
      {/* LEFT COLUMN: List / Grid of Recipes */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        {/* Filter Controls Panel */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1.25rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', position: 'relative' }}>
            <input 
              type="text" 
              className="form-input" 
              placeholder="Search recipes (e.g. wings, curry, soup)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ flexGrow: 1, paddingLeft: '2.5rem' }}
            />
            <Search size={18} style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--text-muted))' }} />
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center' }}>
            {/* Culture dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'hsl(var(--text-secondary))', textTransform: 'uppercase', fontWeight: '600' }}>Cuisine:</span>
              <select 
                value={selectedCulture} 
                onChange={(e) => setSelectedCulture(e.target.value)}
                style={{ background: 'hsl(var(--bg-app))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--text-primary))', padding: '0.35rem 0.75rem', borderRadius: '8px', outline: 'none' }}
              >
                <option value="">All Cuisines</option>
                {CULTURES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            {/* Season dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'hsl(var(--text-secondary))', textTransform: 'uppercase', fontWeight: '600' }}>Season:</span>
              <select 
                value={selectedSeason} 
                onChange={(e) => setSelectedSeason(e.target.value)}
                style={{ background: 'hsl(var(--bg-app))', border: '1px solid hsl(var(--border))', color: 'hsl(var(--text-primary))', padding: '0.35rem 0.75rem', borderRadius: '8px', outline: 'none' }}
              >
                <option value="">All Seasons</option>
                {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {(selectedCulture || selectedSeason || search) && (
              <button 
                onClick={() => { setSelectedCulture(''); setSelectedSeason(''); setSearch(''); }}
                style={{ fontSize: '0.8rem', background: 'transparent', color: 'hsl(var(--danger))', textDecoration: 'underline' }}
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Recipes Grid */}
        <div className="custom-scroll" style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 270px)', paddingRight: '0.25rem' }}>
          
          {/* Onboarding Matches Section */}
          {initialRecipes.length > 0 && !search && !selectedCulture && !selectedSeason && (
            <div style={{ marginBottom: '2rem' }}>
              <h3 style={{ fontSize: '1rem', fontFamily: 'var(--font-display)', fontWeight: '700', color: 'hsl(var(--primary))', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <BookOpen size={16} />
                <span>✨ Your Personalized Matches</span>
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {initialRecipes.map(recipe => {
                  const isActive = selectedRecipe?.id === recipe.id;
                  
                  // Calculate pantry matches
                  const matches = recipe.ingredients.map(ing => checkIngredientMatch(ing));
                  const matchedCount = matches.filter(m => m.matched).length;
                  const totalCount = recipe.ingredients.length;
                  const percent = Math.round((matchedCount / totalCount) * 100);

                  return (
                    <div 
                      key={`init-${recipe.id}`}
                      className="card"
                      onClick={() => handleSelectRecipe(recipe)}
                      style={{ 
                        padding: '1.25rem', 
                        cursor: 'pointer',
                        borderColor: isActive ? 'hsl(var(--primary))' : 'hsl(var(--primary) / 0.3)',
                        background: isActive ? 'rgba(16, 185, 129, 0.06)' : 'rgba(16, 185, 129, 0.01)',
                        boxShadow: '0 0 10px rgba(16, 185, 129, 0.02)'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <h3 className="recipe-card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span>{recipe.name}</span>
                          <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.15)', color: '#a7f3d0' }}>Match</span>
                        </h3>
                        <ChevronRight size={18} style={{ color: 'hsl(var(--text-muted))', transform: isActive ? 'rotate(90deg)' : '', transition: '0.2s' }} />
                      </div>

                      <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.85rem', lineHeight: '1.4', margin: '0.25rem 0 0.75rem 0', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {recipe.description}
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div className="recipe-tags" style={{ margin: 0 }}>
                          {recipe.tags.slice(0, 3).map(tag => {
                            let type = 'tag-culture';
                            if (SEASONS.map(s=>s.toLowerCase()).includes(tag.toLowerCase())) type = 'tag-season';
                            if (['airfryer', 'oven', 'stove', 'mixer', 'microwave', 'slow-cooker'].includes(tag.toLowerCase())) type = 'tag-appliance';
                            if (['gluten-free', 'lactose-free', 'vegetarian', 'vegan', 'low-carb'].includes(tag.toLowerCase())) type = 'tag-restriction';
                            return (
                              <span key={tag} className={`tag ${type}`}>{tag}</span>
                            );
                          })}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.8rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'hsl(var(--text-secondary))' }}>
                            <Clock size={12} />
                            <span>{recipe.minutes} mins</span>
                          </div>
                          <div 
                            style={{ 
                              padding: '0.25rem 0.5rem', 
                              borderRadius: '6px', 
                              background: percent === 100 ? 'rgba(16, 185, 129, 0.15)' : percent > 40 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                              color: percent === 100 ? '#a7f3d0' : percent > 40 ? '#fde68a' : '#fecdd3',
                              fontWeight: '600'
                            }}
                          >
                            {matchedCount}/{totalCount} Ingredients ({percent}%)
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={{ margin: '1.5rem 0 1rem 0', height: '1px', background: 'hsl(var(--border))' }}></div>
              <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '0.05em', color: 'hsl(var(--text-secondary))', marginBottom: '0.75rem' }}>
                All Recipes Database
              </h3>
            </div>
          )}

          {recipes.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
              <AlertTriangle size={32} style={{ color: 'hsl(var(--text-muted))', marginBottom: '0.5rem', display: 'inline' }} />
              <p style={{ color: 'hsl(var(--text-secondary))' }}>No recipes match your criteria.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {recipes.map(recipe => {
                const isActive = selectedRecipe?.id === recipe.id;
                
                // Calculate pantry matches
                const matches = recipe.ingredients.map(ing => checkIngredientMatch(ing));
                const matchedCount = matches.filter(m => m.matched).length;
                const totalCount = recipe.ingredients.length;
                const percent = Math.round((matchedCount / totalCount) * 100);

                return (
                  <div 
                    key={recipe.id}
                    className="card"
                    onClick={() => handleSelectRecipe(recipe)}
                    style={{ 
                      padding: '1.25rem', 
                      cursor: 'pointer',
                      borderColor: isActive ? 'hsl(var(--primary))' : '',
                      background: isActive ? 'rgba(16, 185, 129, 0.03)' : ''
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <h3 className="recipe-card-title">{recipe.name}</h3>
                      <ChevronRight size={18} style={{ color: 'hsl(var(--text-muted))', transform: isActive ? 'rotate(90deg)' : '', transition: '0.2s' }} />
                    </div>

                    <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.85rem', lineHeight: '1.4', margin: '0.25rem 0 0.75rem 0', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {recipe.description}
                    </p>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div className="recipe-tags" style={{ margin: 0 }}>
                        {recipe.tags.slice(0, 3).map(tag => {
                          let type = 'tag-culture';
                          if (SEASONS.map(s=>s.toLowerCase()).includes(tag.toLowerCase())) type = 'tag-season';
                          if (['airfryer', 'oven', 'stove', 'mixer', 'microwave', 'slow-cooker'].includes(tag.toLowerCase())) type = 'tag-appliance';
                          if (['gluten-free', 'lactose-free', 'vegetarian', 'vegan', 'low-carb'].includes(tag.toLowerCase())) type = 'tag-restriction';
                          return (
                            <span key={tag} className={`tag ${type}`}>{tag}</span>
                          );
                        })}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.8rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'hsl(var(--text-secondary))' }}>
                          <Clock size={12} />
                          <span>{recipe.minutes} mins</span>
                        </div>
                        <div 
                          style={{ 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: '6px', 
                            background: percent === 100 ? 'rgba(16, 185, 129, 0.15)' : percent > 40 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                            color: percent === 100 ? '#a7f3d0' : percent > 40 ? '#fde68a' : '#fecdd3',
                            fontWeight: '600'
                          }}
                        >
                          {matchedCount}/{totalCount} Ingredients ({percent}%)
                        </div>
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* RIGHT COLUMN: Detail View of Selected Recipe */}
      {selectedRecipe && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', position: 'sticky', top: '100px', maxHeight: 'calc(100vh - 140px)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid hsl(var(--border))', paddingBottom: '1rem' }}>
            <div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: '800' }}>{selectedRecipe.name}</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', color: 'hsl(var(--text-secondary))', fontSize: '0.875rem' }}>
                <Clock size={14} />
                <span>{selectedRecipe.minutes} minutes</span>
                <span>•</span>
                <span style={{ textTransform: 'capitalize' }}>{selectedRecipe.description}</span>
              </div>
            </div>
            <button 
              onClick={() => setSelectedRecipe(null)}
              style={{ padding: '0.25rem', color: 'hsl(var(--text-muted))', background: 'transparent' }}
            >
              <X size={20} />
            </button>
          </div>

          <div className="custom-scroll" style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.5rem', paddingRight: '0.25rem' }}>
            
            {/* Ingredients Check Section */}
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.025em', color: 'hsl(var(--text-secondary))' }}>
                Ingredients Check
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {selectedRecipe.ingredients.map((ing, idx) => {
                  const check = checkIngredientMatch(ing);
                  return (
                    <div 
                      key={idx}
                      style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        padding: '0.5rem 0.75rem', 
                        background: check.matched ? 'rgba(16, 185, 129, 0.02)' : 'rgba(244, 63, 94, 0.02)',
                        border: '1px solid',
                        borderColor: check.matched ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                        borderRadius: '8px',
                        fontSize: '0.9rem'
                      }}
                    >
                      <span style={{ textTransform: 'capitalize', fontWeight: '500', color: check.matched ? '#fff' : 'hsl(var(--text-secondary))' }}>
                        {ing}
                      </span>
                      {check.matched ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'hsl(var(--primary))', fontSize: '0.8rem', fontWeight: '600' }}>
                          <Check size={14} />
                          <span>In Stock</span>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#f43f5e', fontSize: '0.8rem', fontWeight: '600' }}>
                          <X size={14} />
                          <span>Missing</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Step-by-Step Cooking Guide */}
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.025em', color: 'hsl(var(--text-secondary))' }}>
                Step-by-Step Cooking Guide
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {selectedRecipe.steps.map((step, idx) => {
                  const checked = checkedSteps[idx];
                  return (
                    <div 
                      key={idx}
                      onClick={() => toggleStep(idx)}
                      style={{ 
                        display: 'flex', 
                        gap: '0.75rem', 
                        padding: '1rem', 
                        background: checked ? 'rgba(16, 185, 129, 0.04)' : 'rgba(255, 255, 255, 0.01)',
                        border: '1px solid',
                        borderColor: checked ? 'rgba(16, 185, 129, 0.2)' : 'hsl(var(--border))',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        transition: 'var(--transition-fast)'
                      }}
                    >
                      <div 
                        style={{ 
                          height: '20px', 
                          width: '20px', 
                          borderRadius: '6px', 
                          border: '2px solid',
                          borderColor: checked ? 'hsl(var(--primary))' : 'hsl(var(--border))',
                          background: checked ? 'hsl(var(--primary))' : 'transparent',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: '#0c111d',
                          flexShrink: 0,
                          marginTop: '0.1rem'
                        }}
                      >
                        {checked && <Check size={12} strokeWidth={3} />}
                      </div>
                      <div style={{ fontSize: '0.95rem', lineHeight: '1.4', color: checked ? 'hsl(var(--text-muted))' : 'hsl(var(--text-primary))', textDecoration: checked ? 'line-through' : 'none' }}>
                        <span style={{ fontWeight: '700', color: checked ? 'hsl(var(--text-muted))' : 'hsl(var(--primary))', marginRight: '0.5rem' }}>
                          Step {idx + 1}
                        </span>
                        {step}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

export default RecipeBrowser;
