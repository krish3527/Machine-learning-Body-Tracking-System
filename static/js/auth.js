/**
 * auth.js
 * ApexMotion Authentication Client Logic.
 * Manages Login / Register tabs, validation, credential submission, and redirects.
 */

document.addEventListener("DOMContentLoaded", () => {
  const tabBtnLogin = document.getElementById("tab-btn-login");
  const tabBtnRegister = document.getElementById("tab-btn-register");
  const formLogin = document.getElementById("form-login");
  const formRegister = document.getElementById("form-register");
  const authAlert = document.getElementById("auth-alert");
  const linkGotoRegister = document.getElementById("link-goto-register");
  const linkGotoLogin = document.getElementById("link-goto-login");

  // Get next redirect target from URL query params
  const urlParams = new URLSearchParams(window.location.search);
  const nextUrl = urlParams.get("next") || "/";
  const initialMode = urlParams.get("mode") || "login";

  function showAlert(message, type = "error") {
    if (!authAlert) return;
    authAlert.textContent = message;
    authAlert.className = `auth-alert ${type}`;
    authAlert.style.display = "block";
  }

  function hideAlert() {
    if (!authAlert) return;
    authAlert.style.display = "none";
  }

  function switchTab(target) {
    hideAlert();
    if (target === "register") {
      tabBtnRegister.classList.add("active");
      tabBtnLogin.classList.remove("active");
      formRegister.style.display = "block";
      formLogin.style.display = "none";
      const nameInput = document.getElementById("register-name");
      if (nameInput) nameInput.focus();
    } else {
      tabBtnLogin.classList.add("active");
      tabBtnRegister.classList.remove("active");
      formLogin.style.display = "block";
      formRegister.style.display = "none";
      const emailInput = document.getElementById("login-email");
      if (emailInput) emailInput.focus();
    }
  }

  if (tabBtnLogin) tabBtnLogin.addEventListener("click", () => switchTab("login"));
  if (tabBtnRegister) tabBtnRegister.addEventListener("click", () => switchTab("register"));
  if (linkGotoRegister) linkGotoRegister.addEventListener("click", () => switchTab("register"));
  if (linkGotoLogin) linkGotoLogin.addEventListener("click", () => switchTab("login"));

  // Check initial mode from query
  if (initialMode === "register") {
    switchTab("register");
  }

  // Demo fill buttons
  document.querySelectorAll(".btn-demo-fill").forEach(btn => {
    btn.addEventListener("click", () => {
      const email = btn.getAttribute("data-email");
      const pass = btn.getAttribute("data-pass");
      const emailInput = document.getElementById("login-email");
      const passInput = document.getElementById("login-password");
      if (emailInput) emailInput.value = email;
      if (passInput) passInput.value = pass;
      switchTab("login");
    });
  });

  // 1. LOGIN SUBMISSION
  if (formLogin) {
    formLogin.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideAlert();

      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;
      const btnSubmit = document.getElementById("btn-login-submit");

      if (!email || !password) {
        showAlert("Please enter both email and password.");
        return;
      }

      btnSubmit.disabled = true;
      btnSubmit.textContent = "Logging in...";

      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "Invalid email or password.");
        }

        showAlert(`Welcome back, ${data.user.name}! Redirecting...`, "success");
        setTimeout(() => {
          window.location.href = nextUrl;
        }, 400);

      } catch (err) {
        showAlert(err.message, "error");
        btnSubmit.disabled = false;
        btnSubmit.textContent = "Login \u2192";
      }
    });
  }

  // 2. REGISTER SUBMISSION
  if (formRegister) {
    formRegister.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideAlert();

      const name = document.getElementById("register-name").value.trim();
      const email = document.getElementById("register-email").value.trim();
      const password = document.getElementById("register-password").value;
      const confirmPassword = document.getElementById("register-confirm-password").value;
      const btnSubmit = document.getElementById("btn-register-submit");

      // Validations
      if (!name) {
        showAlert("Please enter your name.");
        return;
      }
      if (!email || !email.includes("@") || !email.includes(".")) {
        showAlert("Please enter a valid email address.");
        return;
      }
      if (!password) {
        showAlert("Password cannot be empty.");
        return;
      }
      if (password.length < 4) {
        showAlert("Password must be at least 4 characters long.");
        return;
      }
      if (password !== confirmPassword) {
        showAlert("Passwords do not match. Please verify.");
        return;
      }

      btnSubmit.disabled = true;
      btnSubmit.textContent = "Creating Account...";

      try {
        const res = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            email,
            password,
            confirm_password: confirmPassword
          })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "Failed to create account.");
        }

        showAlert(`Account created! Welcome to ApexMotion, ${data.user.name}. Redirecting...`, "success");
        setTimeout(() => {
          window.location.href = nextUrl;
        }, 500);

      } catch (err) {
        showAlert(err.message, "error");
        btnSubmit.disabled = false;
        btnSubmit.textContent = "Create Account \u2192";
      }
    });
  }
});
