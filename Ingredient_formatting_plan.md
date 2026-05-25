This file contains the plan for the Ingredient Formatting feature. It is meant to act as guide and reference when implementing changes regarding this feature. 

We need to implement a feature that will format ingredients, so they can be stored in the database.

When the user sends messages that contain information about ingredients that they acquired, we need to extract that information, run it through a knowledge base file containing the "correct" names for each of those ingredients, and store it in the database.

Implementation Plan:
1. Create a file that will be used as that knowledge base. This file must contain a list of ingredients that can be used as a reference to format the ingredients that the user sends, as well as synonyms if there are any commom ones. This file must include most ingredients that are commomly bought and used in ocidental household cooking.

2. Modify the database of recipes to include all ingredients used by each recipe. This ingredients must first be run through the feature mentioned before, to ensure that the names saved to the database are standardized.

3. Add this feature to the graph of the assistant.

OPEN QUESTIONS: 
- What form will this feature have? Should it be a Tool, a Skill, or a Subagent? Investigate what would be the best implementation for the feature, and the reasoning behind it. Ideally we want to have accuracy as a focus, minimizing hallucinations, but also taking into account the token cost it would create.
- What would be the best way to create and populate the knowledge base of ingredients?