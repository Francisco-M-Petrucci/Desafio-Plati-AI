This document is meant to act as a guide and reference for the implementation of a cooking assistance mode. 

OBJECTIVE: To create a cooking assistance mode that will extract the steps of the requested recipe, and run them through the LLM to output a more detailed step-by-step instructions 
for the user to follow.

INTERACTION FLOW: 
1. When the user asks for the steps of a specific recipe, the agent will retrieve and output them (through the get_recipe_details_tool). In the instance o