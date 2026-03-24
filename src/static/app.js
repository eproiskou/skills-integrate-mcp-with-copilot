document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");

  const loginForm = document.getElementById("login-form");
  const createAccountForm = document.getElementById("create-account-form");
  const logoutButton = document.getElementById("logout-button");
  const authStatus = document.getElementById("auth-status");
  const authForms = document.getElementById("auth-forms");
  const signupHint = document.getElementById("signup-hint");

  let currentUser = null;

  function showMessage(text, type = "success") {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function updateAuthUI() {
    if (currentUser) {
      authStatus.textContent = `Logged in as ${currentUser.email} (${currentUser.role})`;
      authForms.classList.add("hidden");
      logoutButton.classList.remove("hidden");
      signupHint.textContent = "You are authenticated and can register for activities.";
    } else {
      authStatus.textContent = "You are not logged in.";
      authForms.classList.remove("hidden");
      logoutButton.classList.add("hidden");
      signupHint.textContent = "Please log in to register for activities.";
    }
  }

  async function authFetch(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    let data = {};
    try {
      data = await response.json();
    } catch (err) {
      // Keep empty object if response has no JSON body.
    }

    if (!response.ok) {
      const detail = data.detail || "Request failed";
      throw new Error(detail);
    }

    return data;
  }

  async function fetchSession() {
    try {
      const data = await authFetch("/auth/me", { method: "GET" });
      currentUser = data.user;
    } catch (error) {
      currentUser = null;
    }

    updateAuthUI();
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities", { credentials: "same-origin" });
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participants.length;

        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map((email) => {
                    const canUnregister =
                      currentUser &&
                      (currentUser.role === "admin" || currentUser.email === email);
                    const unregisterButton = canUnregister
                      ? `<button class="delete-btn" data-activity="${name}" data-email="${email}">❌</button>`
                      : "";
                    return `<li><span class="participant-email">${email}</span>${unregisterButton}</li>`;
                  })
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const data = await authFetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );

      showMessage(data.message, "success");
      fetchActivities();
    } catch (error) {
      showMessage(error.message, "error");
      console.error("Error unregistering:", error);
    }
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
      await authFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      await fetchSession();
      await fetchActivities();
      loginForm.reset();
      showMessage("Login successful", "success");
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  createAccountForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("signup-email").value;
    const password = document.getElementById("signup-password").value;
    const role = document.getElementById("signup-role").value;

    try {
      await authFetch("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password, role }),
      });

      createAccountForm.reset();
      showMessage("Account created successfully. Please login.", "success");
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      await authFetch("/auth/logout", { method: "POST" });
      currentUser = null;
      updateAuthUI();
      await fetchActivities();
      showMessage("Logged out successfully", "success");
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = document.getElementById("activity").value;

    if (!currentUser) {
      showMessage("Please login first.", "error");
      return;
    }

    try {
      const data = await authFetch(
        `/activities/${encodeURIComponent(activity)}/signup`,
        { method: "POST" }
      );

      signupForm.reset();
      showMessage(data.message, "success");
      fetchActivities();
    } catch (error) {
      showMessage(error.message, "error");
      console.error("Error signing up:", error);
    }
  });

  async function init() {
    await fetchSession();
    await fetchActivities();
  }

  init();
});
