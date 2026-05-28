# Recipe App - Demonstration Sequence

This document outlines a simple sequence of events to demonstrate the key functionalities of the Recipe Application using the pre-seeded accounts: **Alice** and **Bob**.

These accounts have been specially crafted to yield different recipe results, showcasing the app's capability to tailor recommendations based on individual profiles (appliances, ingredients, and dietary restrictions).

---

## 1. Alice's Experience: The Health-Conscious Quick Cook

**Profile Summary:**
*   **Appliances:** Stove, Airfryer, Blender/Mixer
*   **Dietary Restrictions:** Gluten-Free
*   **Vibe:** "Prefers quick and easy meals", "Loves savory flavors"
*   **Key Ingredients:** Chicken wings, sweet potatoes, parmesan cheese, cilantro, lime juice, olive oil.

### Step-by-Step Sequence

1.  **Log In:** Open the application and log in with username `alice` and password `password123`.
2.  **Initial Dashboard:**
    *   Observe the "Suggested for you" recipes on the Recipe Explorer.
    *   *Agent Capability:* Notice that the initial recipes are heavily skewed towards her ingredients (e.g., *Airfryer Garlic Parmesan Chicken Wings*, *Airfryer Sweet Potato Fries*) and strictly adhere to her **gluten-free** dietary restriction.
3.  **Chat Interaction - Direct Request:**
    *   Open the cooking assistant chat.
    *   Type: *"I'm really hungry and I only have about 20 minutes to cook something. What can I make with my chicken wings?"*
    *   *Agent Capability:* The agent should use Alice's facts ("Prefers quick and easy meals"), check her ingredients, and recommend a fast chicken wings recipe using her airfryer.
4.  **Chat Interaction - Dietary Safety Check:**
    *   Type: *"Can I make a classic pasta dish?"*
    *   *Agent Capability:* The system features a strict, invisible safety filter that runs in the backend *before* the AI even sees the search results. Because all classic pasta recipes in the database contain gluten, the backend completely strips them out. The AI will only present safe, 100% gluten-free alternatives (like Caprese Salad or Salmon). This showcases the application's robust architecture: there is **ZERO RISK** of the agent hallucinating or recommending a dangerous recipe that violates the user's dietary restrictions!

---

## 2. Bob's Experience: The Traditional Italian Vegetarian

**Profile Summary:**
*   **Appliances:** Oven, Stove, Microwave, Blender/Mixer
*   **Dietary Restrictions:** Vegetarian
*   **Vibe:** "Loves authentic Italian food", "Dislikes spicy food"
*   **Key Ingredients:** Pizza dough, fresh mozzarella cheese, canned san marzano tomatoes, fresh basil leaves, penne pasta, eggs.

### Step-by-Step Sequence

1.  **Log In:** Log out from Alice's account and log in with username `bob` and password `password123`.
2.  **Initial Dashboard:**
    *   Observe the "Suggested for you" recipes.
    *   *Agent Capability:* Notice how completely different the suggestions are compared to Alice. Bob's dashboard will feature **vegetarian** dishes, particularly Italian classics like *Classic Italian Margherita Pizza* or *Roasted Garlic Parmesan Asparagus*, perfectly matching his ingredients and oven/stove setup.
3.  **Chat Interaction - Vibe Check:**
    *   Open the cooking assistant chat.
    *   Type: *"I want to make something really spicy for dinner, just for tonight."*
    *   *Agent Capability:* The agent should refer to Bob's long-term facts ("Dislikes spicy food") and gently remind him or ask if he's sure, demonstrating personalized memory.
4.  **Chat Interaction - Database vs General Knowledge:**
    *   Type: *"I have some pizza dough and fresh mozzarella. Walk me through making a pizza step-by-step."*
    *   *Agent Capability:* Notice that the agent answers how to make a generic pizza from its own general knowledge without accessing the database.
    *   Then, type: *"Walk me through making a margherita pizza step-by-step."*
    *   *Agent Capability:* Notice that the agent will fetch the *Classic Italian Margherita Pizza* recipe from the database instead. This shows that the agent is still able to answer basic cooking questions, but prioritizes the database when possible.

---

## What This Demo Highlights:

*   **Robust Filtering:** The system strictly enforces dietary restrictions (Gluten-Free vs. Vegetarian) and appliance availability (Airfryer vs. Oven).
*   **Smart Ingredient Matching:** The vector search accurately pulls up recipes that heavily overlap with the user's current fridge contents.
*   **Personalized Agent Persona:** The LLM acts differently based on long-term user facts, making the interaction feel custom-tailored to the specific user.
