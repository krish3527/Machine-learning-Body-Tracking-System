/**
 * workout_plan.js
 * ApexMotion Balanced Random Workout Plan Generator.
 * Generates dynamic workout sets with reps, duration, and rest intervals.
 */

document.addEventListener("DOMContentLoaded", () => {
  const btnGeneratePlan = document.getElementById("btn-generate-plan");
  const planContainer = document.getElementById("workout-plan-container");
  const planDifficulty = document.getElementById("plan-difficulty");
  const planEstTime = document.getElementById("plan-est-time");

  if (!btnGeneratePlan) return;

  btnGeneratePlan.addEventListener("click", fetchAndRenderPlan);

  async function fetchAndRenderPlan() {
    btnGeneratePlan.disabled = true;
    btnGeneratePlan.innerHTML = `Generating...`;

    try {
      const res = await fetch("/api/generate_plan");
      const data = await res.json();

      if (planDifficulty) planDifficulty.textContent = data.difficulty;
      if (planEstTime) planEstTime.textContent = data.estimated_duration;

      if (planContainer && data.exercises) {
        planContainer.innerHTML = "";
        data.exercises.forEach((item, idx) => {
          const card = document.createElement("div");
          card.className = "plan-exercise-card";
          card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.25rem;">
              <span style="font-weight: 700; font-size: 1.05rem; color: var(--text-main);">
                ${idx + 1}. ${item.name}
              </span>
              <span class="plan-tag">${item.category}</span>
            </div>
            <div style="display: flex; gap: 1.25rem; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.35rem;">
              <span><strong>Sets:</strong> ${item.sets} &times;</span>
              <span><strong>Work:</strong> ${item.reps}</span>
              <span><strong>Rest:</strong> ${item.rest}</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-light); font-style: italic;">
              &bull; ${item.tip}
            </div>
          `;
          planContainer.appendChild(card);
        });
      }
    } catch (e) {
      console.error("Error generating plan:", e);
    } finally {
      btnGeneratePlan.disabled = false;
      btnGeneratePlan.innerHTML = `&#8635; Regenerate Workout Plan`;
    }
  }

  // Load initial plan if container exists and is empty
  if (planContainer && planContainer.children.length === 0) {
    fetchAndRenderPlan();
  }
});
