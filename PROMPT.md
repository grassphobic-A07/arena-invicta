You are an expert **web developer and software consultant**.

You will help me implement a Flask web application that uses **TailwindCSS** for styling.  
The main focus is to develop the **`discussions` app/module**, which will integrate with the existing `news` app.

---

## 🧩 Context
- The project is a Flask-based web app with TailwindCSS.
- The `news` app already exists and provides examples of AJAX usage, responsive layouts, and frontend behavior.
- Your implementation should follow similar structure and design patterns as the `news` app.
- The templating (HTML, Jinja2) is currently minimal — your goal is to make it functional first.

---

## 🚀 Tasks to Implement (`discussions` app)

### 1. Core Functionality
- Implement a **list of discussions (threads)**.
- Each discussion should:
  - Contain a **link to the corresponding news item** being discussed.
  - Display **thread metadata**: creator’s profile picture, thread title, creation date, etc.
- Add a **search feature** that allows filtering discussions by:
  - The **news title**, or
  - The **UUID** of the related news.

### 2. Frontend (AJAX & Responsiveness)
- Implement an **AJAX-powered "Add Thread"** button.
  - Use the same AJAX interaction style as in the `news` app.
- Implement **toast notifications** for success, error, and validation messages.
- Ensure **mobile responsiveness**:
  - Threads should be displayed in card-style rectangles.
  - Include the user’s profile picture, thread title, and metadata clearly.
- Keep the UI consistent with the design of the `news` app.

---

## 🧰 Technical Notes
- Use Flask Blueprints for modularity (`discussions` as its own blueprint).
- Use TailwindCSS utility classes (avoid inline CSS).
- Use JSON endpoints for AJAX routes.
- All CRUD operations (especially Add Thread) must work asynchronously.
- Write clear commit messages or bullet points about what was implemented.

---

## 📄 Reporting
When you are done, document all changes in **`CHANGES.md`** with the following sections:
1. **Added** – New features, files, or routes.
2. **Modified** – Updated templates, CSS, or routes.
3. **Fixed** – Any bugs or inconsistencies corrected.
4. **Notes** – Any assumptions, known issues, or follow-up improvements.

---

## ✅ Output Format
When responding, please include:
- Flask route definitions (in Python)
- Corresponding Jinja2 templates or HTML snippets
- JavaScript snippets for AJAX calls
- A summary of changes suitable for inclusion in `CHANGES.md`

Focus on **clarity, reusability, and alignment** with the `news` app’s style.
