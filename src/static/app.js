document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const loginButton = document.getElementById("teacher-login-button");
  const logoutButton = document.getElementById("teacher-logout-button");
  const sessionLabel = document.getElementById("teacher-session-label");
  const loginDialog = document.getElementById("teacher-login-dialog");
  const loginForm = document.getElementById("teacher-login-form");
  const loginError = document.getElementById("login-error");
  let isTeacher = false;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  async function refreshTeacherSession() {
    try {
      const response = await fetch("/auth/session");
      const session = await response.json();
      isTeacher = response.ok && session.authenticated;
      signupContainer.classList.toggle("hidden", !isTeacher);
      loginButton.classList.toggle("hidden", isTeacher);
      logoutButton.classList.toggle("hidden", !isTeacher);
      sessionLabel.textContent = isTeacher ? `Signed in: ${session.username}` : "";
      sessionLabel.classList.toggle("hidden", !isTeacher);
    } catch (error) {
      isTeacher = false;
      signupContainer.classList.add("hidden");
      loginButton.classList.remove("hidden");
      logoutButton.classList.add("hidden");
      sessionLabel.classList.add("hidden");
      console.error("Error checking teacher session:", error);
    }
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map((email) => {
                    const removeButton = isTeacher
                      ? `<button class="delete-btn" type="button" aria-label="Unregister ${email}" title="Unregister student" data-activity="${name}" data-email="${email}">×</button>`
                      : "";
                    return `<li><span class="participant-email">${email}</span>${removeButton}</li>`;
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

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to teacher-only unregister buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
        if (response.status === 401) {
          await refreshTeacherSession();
          fetchActivities();
        }
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
        if (response.status === 401) {
          await refreshTeacherSession();
          fetchActivities();
        }
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  loginButton.addEventListener("click", () => {
    loginError.textContent = "";
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });

  document.getElementById("cancel-teacher-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        loginError.textContent = result.detail || "Sign in failed.";
        loginError.classList.remove("hidden");
        return;
      }
      loginDialog.close();
      loginForm.reset();
      await refreshTeacherSession();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = "Unable to sign in. Please try again.";
      loginError.classList.remove("hidden");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
      await refreshTeacherSession();
      await fetchActivities();
    } catch (error) {
      showMessage("Unable to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  (async () => {
    await refreshTeacherSession();
    await fetchActivities();
  })();
});
