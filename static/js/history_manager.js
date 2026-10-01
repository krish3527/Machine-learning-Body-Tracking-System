/**
 * history_manager.js
 * ApexMotion User-Specific Workout History Manager.
 * Communicates with backend SQLite API (/api/history) to maintain private,
 * isolated workout records for the authenticated user.
 */

const HistoryManager = {
  cache: [],

  async fetchHistory() {
    try {
      const res = await fetch("/api/history");
      if (!res.ok) {
        if (res.status === 401) {
          // Unauthenticated
          return [];
        }
        throw new Error("Failed to load workout history");
      }
      const data = await res.json();
      this.cache = data.workouts || [];
      this.renderDashboard();
      return this.cache;
    } catch (err) {
      console.warn("History fetch notice:", err.message);
      this.renderDashboard();
      return this.cache;
    }
  },

  getAll() {
    return this.cache;
  },

  async addSession(session) {
    const payload = {
      exercise: session.exercise || "Squat",
      reps: session.reps !== undefined ? String(session.reps) : "0",
      form_status: session.form_status || session.form || "Good",
      duration: session.duration || "02:00",
      detected_issues: session.detected_issues || "",
      feedback: session.feedback || ""
    };

    try {
      const res = await fetch("/api/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error("Could not save workout to server");
      }

      const saved = await res.json();
      if (saved.workout) {
        this.cache.unshift(saved.workout);
      }
      this.renderDashboard();
    } catch (err) {
      console.error("Save workout error:", err);
      // Fallback local unshift so user sees immediate feedback
      this.cache.unshift({
        id: "temp-" + Date.now(),
        ...payload
      });
      this.renderDashboard();
    }
  },

  async deleteSession(workoutId) {
    if (!workoutId) return;

    try {
      const res = await fetch(`/api/history/${workoutId}`, {
        method: "DELETE"
      });

      if (!res.ok) {
        throw new Error("Failed to delete workout");
      }

      this.cache = this.cache.filter(w => String(w.id) !== String(workoutId));
      this.renderDashboard();
    } catch (err) {
      console.error("Delete workout error:", err);
      alert("Failed to delete workout record: " + err.message);
    }
  },

  async clear() {
    try {
      const res = await fetch("/api/history", {
        method: "DELETE"
      });

      if (!res.ok) {
        throw new Error("Failed to clear workouts");
      }

      this.cache = [];
      this.renderDashboard();
    } catch (err) {
      console.error("Clear workouts error:", err);
      alert("Could not clear history: " + err.message);
    }
  },

  parseDurationSeconds(durStr) {
    if (!durStr || typeof durStr !== "string") return 0;
    const parts = durStr.split(":").map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return parts[0] * 60 + parts[1];
    }
    return 0;
  },

  formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  },

  renderDashboard() {
    const tableBody = document.getElementById("history-table-body");
    const totalExercisesEl = document.getElementById("dash-total-exercises");
    const totalRepsEl = document.getElementById("dash-total-reps");
    const totalDurationEl = document.getElementById("dash-total-duration");
    const emptyStateEl = document.getElementById("history-empty-state");

    const history = this.cache;

    // Calculate Totals
    let totalRepsCount = 0;
    let totalSeconds = 0;

    history.forEach(item => {
      const repNum = parseInt(item.reps);
      if (!isNaN(repNum)) totalRepsCount += repNum;
      totalSeconds += this.parseDurationSeconds(item.duration);
    });

    if (totalExercisesEl) totalExercisesEl.textContent = history.length;
    if (totalRepsEl) totalRepsEl.textContent = totalRepsCount;
    if (totalDurationEl) totalDurationEl.textContent = this.formatDuration(totalSeconds);

    if (!tableBody) return;

    if (history.length === 0) {
      tableBody.innerHTML = "";
      if (emptyStateEl) emptyStateEl.style.display = "block";
      return;
    }

    if (emptyStateEl) emptyStateEl.style.display = "none";
    tableBody.innerHTML = "";

    history.forEach(item => {
      const tr = document.createElement("tr");
      const formText = item.form_status || item.form || "Good";
      const isGood = formText.toLowerCase().includes("good");

      tr.innerHTML = `
        <td style="font-weight: 600;">${item.exercise}</td>
        <td style="font-weight: 700;">${item.reps}</td>
        <td>
          <span class="history-pill ${isGood ? 'good' : 'warn'}">
            ${formText}
          </span>
        </td>
        <td style="color: var(--text-muted); font-variant-numeric: tabular-nums;">${item.duration}</td>
        <td style="text-align: right;">
          <button type="button" class="btn-delete-workout" data-id="${item.id}" title="Delete this workout">
            Delete
          </button>
        </td>
      `;

      // Bind delete handler
      const delBtn = tr.querySelector(".btn-delete-workout");
      if (delBtn) {
        delBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          const wId = delBtn.getAttribute("data-id");
          if (confirm(`Delete this ${item.exercise} record?`)) {
            HistoryManager.deleteSession(wId);
          }
        });
      }

      tableBody.appendChild(tr);
    });
  }
};

window.HistoryManager = HistoryManager;

document.addEventListener("DOMContentLoaded", () => {
  // Automatically load private user workouts on page ready
  HistoryManager.fetchHistory();

  const clearBtn = document.getElementById("btn-clear-history");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (confirm("Clear your entire private exercise history? This cannot be undone.")) {
        HistoryManager.clear();
      }
    });
  }
});
