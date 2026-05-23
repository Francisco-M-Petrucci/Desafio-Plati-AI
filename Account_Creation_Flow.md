This documents details the step by step flow of the new user registration. It is meant to be used as a guideline when implementing changes to the application or fixing bugs related to the account creation process.

1. User enters the login page in the frontend and clicks on "create account".
2. User fills in the form (First name, username, password).
3. The user is then redirected to a page with selectable buttons (with images/icons) that contain normal kitchen appliances, and instructed to select all the appliances that they have in their kitchen (use the ones we already defined to the backend).
4. After submiting that, the user is led to a page with selectable buttons (with images/icons) of dietary restrictions (use the ones we already defined to the backend).
5. The user is then led to a ingredient selection page, with cards (with images/icons) of ingredients commonly found in households. The user should be able to scroll through the ingredients and select the ones they have. The interface should be simple and easy to use.
-Populate this list of ingredients with the most common ones, try to find a list of common ingredients in the internet. The user must be able to select of how much or how many of each ingredient they have.
-Add a submit form at the bottom so that the user is able to submit ingredients that they didn't find in the list.
6. The user clicks on the submit button and the frontend sends the list of selected appliances, dietary restrictions and ingredients to the backend.
7. The backend stores the list of selected appliances, dietary restrictions and ingredients in the database, along with other necessary information (such as creating an user id).
8. Now, the user is led to a "Please wait while we create your account" page. In the background, the search recipes tool should run (with retrieve steps = false) using the user's information (appliances, ingredients and dietary restrictions) and find 5 recipes that match. The same logic used in the assistant should apply:
-First, filtering out any recipes that the user can't perform for lack of proper cooking appliances.
-Then, filtering out any recipes that the user can't consume due to dietary restrictions.
-Finally, using the search recipes tool to find recipes that match the user's available ingredients.

The retrieved list of 5 recipes is then stored (only their recipe_id) in the user's database, in an "Innitial search" list that is tied to that user's id.

9. Once the database update and tool execution is complete, the user is redirected to the main dashboard/home page.
10. To log in to an account from the login page, the user must input their username and password.
11. After submitting, the backend checks if the username and password are correct. If they are, the user is redirected to the main dashboard/home page. If not, the user is redirected to the login page and shown an error message.

Extra notes:
- The user is able to edit their information (appliances, dietary restrictions, ingredients) at any time from their profile page.
-For now, do not remove the buttons for the accounts bob and alice, as they are suited for quick testing.