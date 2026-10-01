/**
 * animated_skeleton.js
 * ApexMotion Dynamic Movement Correction & Animated Form Guide.
 * Demonstrates the EXACT exercise performed by the user (Squat, Push-up, Yoga):
 * - Squat: Standing -> Squat down -> Bottom position -> Return to standing
 * - Push-up: Plank -> Lower body -> Bottom position -> Push back up
 * - Yoga: Target posture alignment comparison
 *
 * Visually contrasts:
 *   1. User Movement (Demonstrating detected flaw: forward lean, shallow depth, knees inward, sagging hips, etc.)
 *   2. Correct Movement (Demonstrating recommended biomechanical alignment)
 */

class AnimatedSkeleton {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.animationId = null;
    this.exercise = "squat"; // 'squat', 'pushup', or 'yoga'
    this.flawType = "squat_lean"; // 'squat_lean', 'squat_shallow', 'squat_knee_valgus', 'pushup_sagging_hips', 'pushup_shallow', 'pushup_elbow_flare'
    
    // View modes: 'compare' (alternates User then Correct), 'user' (user only), 'correct' (correct only)
    this.viewMode = "compare"; 
    this.speedMultiplier = 1.0; // 1.0x or 0.5x
    this.isPlaying = true;
    this.startTime = null;
    this.currentCycle = "user"; // 'user' or 'correct'
    this.repProgress = 0; // 0.0 to 1.0 within one repetition cycle
  }

  // Kinematic Keyframes for Exercises
  static get KINEMATICS() {
    return {
      "squat": {
        name: "Squat Movement Cycle",
        view: "side",
        stages: ["1. Standing", "2. Squatting Down", "3. Bottom Depth", "4. Drive Up"],
        // Neutral Standing Position (Start and Finish)
        standing: {
          head: [165, 45],
          neck: [165, 65],
          shoulder: [165, 80],
          elbow: [150, 110],
          wrist: [135, 120],
          hip: [170, 140],
          knee: [170, 195],
          ankle: [170, 245],
          toe: [145, 245]
        },
        // Flaw 1: Excessive Forward Lean
        lean_bottom_user: {
          head: [115, 80],
          neck: [130, 95],
          shoulder: [135, 105], // Pitched forward 48 deg
          elbow: [115, 130],
          wrist: [95, 140],
          hip: [205, 165],
          knee: [175, 205],
          ankle: [175, 245],
          toe: [145, 245]
        },
        lean_bottom_correct: {
          head: [165, 60],
          neck: [165, 80],
          shoulder: [165, 95], // Upright neutral spine
          elbow: [145, 125],
          wrist: [130, 135],
          hip: [210, 175],
          knee: [165, 205],
          ankle: [165, 245],
          toe: [140, 245]
        },
        // Flaw 2: Shallow Squat Depth
        shallow_bottom_user: {
          head: [165, 55],
          neck: [165, 75],
          shoulder: [165, 90],
          elbow: [145, 120],
          wrist: [130, 130],
          hip: [195, 150], // Stops short of parallel
          knee: [175, 185],
          ankle: [175, 245],
          toe: [145, 245]
        },
        shallow_bottom_correct: {
          head: [165, 75],
          neck: [165, 95],
          shoulder: [165, 110],
          elbow: [145, 135],
          wrist: [130, 145],
          hip: [215, 185], // Hips level with knees (parallel)
          knee: [165, 205],
          ankle: [165, 245],
          toe: [140, 245]
        }
      },

      "squat_knee_valgus": {
        name: "Squat Knee Tracking (Front View)",
        view: "front",
        stages: ["1. Standing", "2. Squatting Down", "3. Bottom Depth", "4. Drive Up"],
        standing: {
          head: [170, 45], neck: [170, 65],
          shoulderL: [135, 85], shoulderR: [205, 85],
          elbowL: [115, 115], elbowR: [225, 115],
          wristL: [135, 140], wristR: [205, 140],
          hipL: [145, 145], hipR: [195, 145],
          kneeL: [140, 195], kneeR: [200, 195],
          ankleL: [130, 245], ankleR: [210, 245],
          footL: [120, 248], footR: [220, 248]
        },
        valgus_bottom_user: {
          head: [170, 75], neck: [170, 95],
          shoulderL: [135, 115], shoulderR: [205, 115],
          elbowL: [115, 140], elbowR: [225, 140],
          wristL: [135, 160], wristR: [205, 160],
          hipL: [145, 175], hipR: [195, 175],
          kneeL: [162, 205], kneeR: [178, 205], // Knees caved inward
          ankleL: [130, 245], ankleR: [210, 245],
          footL: [120, 248], footR: [220, 248]
        },
        valgus_bottom_correct: {
          head: [170, 75], neck: [170, 95],
          shoulderL: [135, 115], shoulderR: [205, 115],
          elbowL: [115, 140], elbowR: [225, 140],
          wristL: [135, 160], wristR: [205, 160],
          hipL: [145, 175], hipR: [195, 175],
          kneeL: [130, 205], kneeR: [210, 205], // Knees aligned over feet
          ankleL: [130, 245], ankleR: [210, 245],
          footL: [120, 248], footR: [220, 248]
        }
      },

      "pushup": {
        name: "Push-up Movement Cycle",
        view: "pushup",
        stages: ["1. Plank", "2. Lowering Body", "3. Chest at Floor", "4. Press Up"],
        // Top Plank Position
        plank_top: {
          head: [65, 105],
          shoulder: [95, 120],
          elbow: [85, 165],
          wrist: [100, 215],
          hip: [185, 150],
          knee: [250, 175],
          ankle: [305, 200],
          toe: [315, 215]
        },
        // Flaw 1: Sagging Hips at Bottom
        sag_bottom_user: {
          head: [65, 145],
          shoulder: [95, 160],
          elbow: [65, 175],
          wrist: [100, 215],
          hip: [185, 195], // Hips sagging towards floor
          knee: [250, 200],
          ankle: [305, 205],
          toe: [315, 215]
        },
        sag_bottom_correct: {
          head: [65, 140],
          shoulder: [95, 155],
          elbow: [65, 175],
          wrist: [100, 215],
          hip: [185, 175], // Straight plank line maintained
          knee: [250, 190],
          ankle: [305, 205],
          toe: [315, 215]
        },
        // Flaw 2: Shallow Pushup Depth
        shallow_bottom_user: {
          head: [65, 120],
          shoulder: [95, 135],
          elbow: [85, 175], // Barely bent arms
          wrist: [100, 215],
          hip: [185, 160],
          knee: [250, 180],
          ankle: [305, 205],
          toe: [315, 215]
        },
        shallow_bottom_correct: {
          head: [65, 150],
          shoulder: [95, 165],
          elbow: [65, 175], // 90 deg elbow, chest down
          wrist: [100, 215],
          hip: [185, 180],
          knee: [250, 195],
          ankle: [305, 205],
          toe: [315, 215]
        }
      },

      "yoga": {
        name: "Yoga Pose Alignment Guide",
        view: "yoga",
        stages: ["1. Prep", "2. Assume Posture", "3. Target Alignment", "4. Hold"],
        bad: {
          head: [165, 50], neck: [165, 70], shoulder: [165, 85],
          elbow: [140, 115], wrist: [120, 125],
          hip: [175, 145], knee: [175, 195], ankle: [175, 245], toe: [150, 245]
        },
        good: {
          head: [165, 45], neck: [165, 65], shoulder: [165, 80],
          elbow: [125, 95], wrist: [100, 95],
          hip: [170, 140], knee: [170, 195], ankle: [170, 245], toe: [145, 245]
        }
      }
    };
  }

  init(flawType = "squat_lean", exerciseName = "squat") {
    if (!this.container) return;
    this.exercise = (exerciseName || "squat").toLowerCase();
    this.flawType = flawType || "squat_lean";

    if (this.flawType.includes("valgus") || this.flawType.includes("knee")) {
      this.exercise = "squat_knee_valgus";
    } else if (this.flawType.includes("pushup") || this.exercise.includes("pushup")) {
      this.exercise = "pushup";
    } else if (this.flawType.includes("yoga") || this.exercise.includes("yoga")) {
      this.exercise = "yoga";
    } else {
      this.exercise = "squat";
    }

    this.renderDOM();
    this.startLoop();
  }

  setCorrectionType(flawType, exerciseName) {
    this.init(flawType, exerciseName);
  }

  replay() {
    this.startTime = null;
    this.isPlaying = true;
    this.currentCycle = "user";
  }

  renderDOM() {
    const isSquat = this.exercise.includes("squat");
    const isPushup = this.exercise === "pushup";
    const titleText = isSquat ? "Squat Biomechanical Movement Guide" : (isPushup ? "Push-up Biomechanical Movement Guide" : "Yoga Posture Alignment Guide");

    this.container.innerHTML = `
      <div class="form-guide-panel" style="position: relative; overflow: hidden;">
        
        <!-- Header & Exercise Title -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
          <div>
            <span class="card-badge" style="font-size: 0.7rem; margin-bottom: 0.2rem;">Animated Human Demonstration</span>
            <h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-main);">${titleText}</h4>
          </div>
          <div style="display: flex; gap: 0.4rem;">
            <button type="button" id="btn-skel-speed" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.72rem;" title="Toggle Slow Motion">
              Speed: <span id="skel-speed-label">1.0x</span>
            </button>
            <button type="button" id="btn-replay-movement" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.72rem;">
              &#8634; Replay
            </button>
          </div>
        </div>

        <!-- Mode Switcher: Compare vs User vs Correct -->
        <div class="guide-mode-switcher">
          <button type="button" class="guide-mode-btn ${this.viewMode === 'compare' ? 'active' : ''}" data-mode="compare">
            &#8646; Auto Compare (User &rarr; Correct)
          </button>
          <button type="button" class="guide-mode-btn ${this.viewMode === 'user' ? 'active' : ''}" data-mode="user">
            &#9888; User Detected Form
          </button>
          <button type="button" class="guide-mode-btn ${this.viewMode === 'correct' ? 'active' : ''}" data-mode="correct">
            &#10003; Recommended Form
          </button>
        </div>

        <!-- Real-Time Movement Stage Pills -->
        <div class="movement-stage-tracker" id="stage-tracker">
          <div class="stage-pill active" id="pill-stage-0">${isPushup ? '1. Plank' : '1. Standing'}</div>
          <div class="stage-pill" id="pill-stage-1">${isPushup ? '2. Lowering' : '2. Squatting Down'}</div>
          <div class="stage-pill" id="pill-stage-2">${isPushup ? '3. Bottom Depth' : '3. Bottom Position'}</div>
          <div class="stage-pill" id="pill-stage-3">${isPushup ? '4. Press Up' : '4. Return to Stand'}</div>
        </div>

        <!-- Mode Indicator Banner -->
        <div id="skel-cycle-banner" style="display: flex; justify-content: space-between; align-items: center; padding: 6px 12px; border-radius: var(--radius-sm); margin-bottom: 0.5rem; font-size: 0.8rem; font-weight: 700; background: var(--status-warn-bg); color: var(--status-warn); border: 1px solid var(--status-warn-border);">
          <span id="skel-cycle-label">&#9888; USER MOVEMENT DETECTED IN VIDEO</span>
          <span id="skel-cycle-cue">Torso leaning too far forward</span>
        </div>

        <!-- SVG Stick Figure Skeleton Viewport -->
        <div style="background-color: var(--bg-subtle); border-radius: var(--radius-md); border: 1px solid var(--border-light); padding: 0.75rem 0.5rem; position: relative;">
          
          <svg id="skel-movement-svg" viewBox="0 0 340 260" style="width: 100%; height: 220px; display: block; margin: 0 auto;">
            <defs>
              <filter id="glow-warn-red" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#ef4444" flood-opacity="0.7"/>
              </filter>
              <filter id="glow-good-green" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#10b981" flood-opacity="0.8"/>
              </filter>
            </defs>

            <!-- Floor Reference Line -->
            <line x1="25" y1="246" x2="315" y2="246" stroke="var(--border-medium)" stroke-width="1.5" stroke-dasharray="4,4"/>

            <!-- Skeleton Layers -->
            <g id="skel-guide-lines"></g>
            <g id="skel-bones"></g>
            <g id="skel-joints"></g>
            <g id="skel-annotations"></g>
          </svg>
        </div>

      </div>
    `;

    // Hook Mode Switchers
    this.container.querySelectorAll(".guide-mode-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        this.container.querySelectorAll(".guide-mode-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.viewMode = btn.getAttribute("data-mode");
        if (this.viewMode === "user") this.currentCycle = "user";
        if (this.viewMode === "correct") this.currentCycle = "correct";
        this.replay();
      });
    });

    // Speed button
    const speedBtn = document.getElementById("btn-skel-speed");
    const speedLabel = document.getElementById("skel-speed-label");
    if (speedBtn) {
      speedBtn.addEventListener("click", () => {
        this.speedMultiplier = this.speedMultiplier === 1.0 ? 0.5 : 1.0;
        speedLabel.textContent = this.speedMultiplier === 0.5 ? "0.5x Slow" : "1.0x";
      });
    }

    // Replay button
    const replayBtn = document.getElementById("btn-replay-movement");
    if (replayBtn) {
      replayBtn.addEventListener("click", () => this.replay());
    }
  }

  startLoop() {
    if (this.animationId) cancelAnimationFrame(this.animationId);

    const animate = (timestamp) => {
      if (!this.startTime) this.startTime = timestamp;
      const effectiveElapsed = (timestamp - this.startTime) * this.speedMultiplier;

      // Each full repetition cycle (start -> down -> bottom -> return) is 3000ms
      const repDuration = 3000;
      const cycleIndex = Math.floor(effectiveElapsed / repDuration);
      const repTime = effectiveElapsed % repDuration;
      const t = repTime / repDuration; // 0.0 to 1.0 in rep

      // Determine which cycle to demonstrate (User vs Correct)
      if (this.viewMode === "compare") {
        this.currentCycle = (cycleIndex % 2 === 0) ? "user" : "correct";
      } else {
        this.currentCycle = this.viewMode;
      }

      this.updateMovementStage(t);
      this.drawKinematicFrame(t);

      this.animationId = requestAnimationFrame(animate);
    };

    this.animationId = requestAnimationFrame(animate);
  }

  updateMovementStage(t) {
    // 4 stages: 0.0-0.2 (Start), 0.2-0.5 (Descent), 0.5-0.7 (Bottom), 0.7-1.0 (Ascent)
    let stageIdx = 0;
    if (t < 0.2) stageIdx = 0;
    else if (t < 0.5) stageIdx = 1;
    else if (t < 0.7) stageIdx = 2;
    else stageIdx = 3;

    for (let i = 0; i < 4; i++) {
      const pill = document.getElementById(`pill-stage-${i}`);
      if (pill) {
        if (i === stageIdx) pill.classList.add("active");
        else pill.classList.remove("active");
      }
    }

    // Update banner text & styling
    const banner = document.getElementById("skel-cycle-banner");
    const label = document.getElementById("skel-cycle-label");
    const cue = document.getElementById("skel-cycle-cue");
    if (!banner || !label || !cue) return;

    if (this.currentCycle === "user") {
      if (this.flawType === "clean") {
        banner.style.background = "var(--status-good-bg)";
        banner.style.borderColor = "var(--status-good-border)";
        banner.style.color = "var(--status-good)";
        label.innerHTML = "&#10003; SOLID REPETITION RECORDED";
        cue.textContent = "Clean movement path with proper joint control";
      } else {
        banner.style.background = "var(--status-warn-bg)";
        banner.style.borderColor = "var(--status-warn-border)";
        banner.style.color = "var(--status-warn)";
        label.innerHTML = "&#9888; USER MOVEMENT (DETECTED IN YOUR VIDEO)";

        if (this.flawType.includes("lean")) cue.textContent = "Torso leaning too far forward during lowering phase";
        else if (this.flawType.includes("shallow")) cue.textContent = "Stopping short before reaching proper depth";
        else if (this.flawType.includes("valgus") || this.flawType.includes("knee")) cue.textContent = "Knees moving inward relative to feet";
        else if (this.flawType.includes("sag")) cue.textContent = "Hips dropping below straight plank line";
        else if (this.flawType.includes("elbow")) cue.textContent = "Elbows flaring excessively outward (90°)";
        else cue.textContent = "Movement execution from video";
      }

    } else {
      banner.style.background = "var(--status-good-bg)";
      banner.style.borderColor = "var(--status-good-border)";
      banner.style.color = "var(--status-good)";
      label.innerHTML = "&#10003; RECOMMENDED CORRECTIVE MOVEMENT";

      if (this.flawType.includes("lean")) cue.textContent = "Chest remains upright & core braced throughout";
      else if (this.flawType.includes("shallow")) cue.textContent = "Full parallel depth achieved with control";
      else if (this.flawType.includes("valgus") || this.flawType.includes("knee")) cue.textContent = "Knees tracking continuously in line with feet";
      else if (this.flawType.includes("sag")) cue.textContent = "Rigid straight line from shoulders through heels";
      else if (this.flawType.includes("elbow")) cue.textContent = "Elbows tucked closer to body (~45° angle)";
      else cue.textContent = "Standard full-range movement mechanics";
    }
  }

  lerp(a, b, factor) {
    return a + (b - a) * factor;
  }

  interpolatePose(poseA, poseB, factor) {
    const res = {};
    for (const k in poseA) {
      if (poseB[k]) {
        res[k] = [
          this.lerp(poseA[k][0], poseB[k][0], factor),
          this.lerp(poseA[k][1], poseB[k][1], factor)
        ];
      }
    }
    return res;
  }

  drawKinematicFrame(t) {
    const bonesG = document.getElementById("skel-bones");
    const jointsG = document.getElementById("skel-joints");
    const guidesG = document.getElementById("skel-guide-lines");
    const annotationsG = document.getElementById("skel-annotations");
    if (!bonesG || !jointsG) return;

    // Movement Curve: 0 -> 1 -> 0 (descent then ascent)
    // t: 0.0 to 0.5 -> depth factor 0 to 1 (descent)
    // t: 0.5 to 1.0 -> depth factor 1 to 0 (ascent)
    let depthFactor = 0;
    if (t <= 0.5) {
      depthFactor = Math.sin((t / 0.5) * (Math.PI / 2)); // Ease out descent
    } else {
      depthFactor = Math.sin(((1.0 - t) / 0.5) * (Math.PI / 2)); // Ease in ascent
    }

    const isUser = this.currentCycle === "user";
    const normalColor = "var(--text-light)";
    const highlightColor = isUser ? "#ef4444" : "#10b981";

    let bonesHTML = "";
    let jointsHTML = "";
    let guidesHTML = "";
    let annotationsHTML = "";

    // 1. SQUAT KINEMATICS
    if (this.exercise === "squat") {
      const data = AnimatedSkeleton.KINEMATICS["squat"];
      const startPose = data.standing;
      
      let bottomPose;
      if (this.flawType.includes("shallow")) {
        bottomPose = isUser ? data.shallow_bottom_user : data.shallow_bottom_correct;
      } else {
        bottomPose = isUser ? data.lean_bottom_user : data.lean_bottom_correct;
      }

      const pts = this.interpolatePose(startPose, bottomPose, depthFactor);

      // Spine color highlight if lean
      const isLeanFlaw = this.flawType.includes("lean");
      const spineColor = isLeanFlaw ? highlightColor : normalColor;
      const legColor = this.flawType.includes("shallow") ? highlightColor : normalColor;

      // Spine & Torso
      bonesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.hip[0]}" y2="${pts.hip[1]}" stroke="${spineColor}" stroke-width="5" stroke-linecap="round"/>`;
      // Neck
      bonesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.neck[0]}" y2="${pts.neck[1]}" stroke="${normalColor}" stroke-width="3" stroke-linecap="round"/>`;
      // Arms
      bonesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.elbow[0]}" y2="${pts.elbow[1]}" stroke="${normalColor}" stroke-width="3.5" stroke-linecap="round"/>`;
      bonesHTML += `<line x1="${pts.elbow[0]}" y1="${pts.elbow[1]}" x2="${pts.wrist[0]}" y2="${pts.wrist[1]}" stroke="${normalColor}" stroke-width="3" stroke-linecap="round"/>`;
      // Legs (Hip -> Knee -> Ankle -> Toe)
      bonesHTML += `<line x1="${pts.hip[0]}" y1="${pts.hip[1]}" x2="${pts.knee[0]}" y2="${pts.knee[1]}" stroke="${legColor}" stroke-width="5" stroke-linecap="round"/>`;
      bonesHTML += `<line x1="${pts.knee[0]}" y1="${pts.knee[1]}" x2="${pts.ankle[0]}" y2="${pts.ankle[1]}" stroke="${normalColor}" stroke-width="4.5" stroke-linecap="round"/>`;
      bonesHTML += `<line x1="${pts.ankle[0]}" y1="${pts.ankle[1]}" x2="${pts.toe[0]}" y2="${pts.toe[1]}" stroke="${normalColor}" stroke-width="4" stroke-linecap="round"/>`;

      // Joints
      jointsHTML += `<circle cx="${pts.head[0]}" cy="${pts.head[1]}" r="14" fill="none" stroke="${highlightColor}" stroke-width="3"/>`;
      jointsHTML += `<circle cx="${pts.head[0]}" cy="${pts.head[1]}" r="6" fill="${highlightColor}"/>`;

      ["shoulder", "elbow", "wrist", "hip", "knee", "ankle"].forEach(j => {
        const p = pts[j];
        const isHighlight = (j === "shoulder" && isLeanFlaw) || (j === "hip" && isLeanFlaw) || (j === "knee");
        jointsHTML += `<circle cx="${p[0]}" cy="${p[1]}" r="${isHighlight ? 6 : 4}" fill="${isHighlight ? highlightColor : normalColor}"/>`;
        jointsHTML += `<circle cx="${p[0]}" cy="${p[1]}" r="2" fill="#ffffff"/>`;
      });

      // Visual Guides & Annotations
      if (depthFactor > 0.6) {
        if (isLeanFlaw) {
          if (isUser) {
            // Forward Lean Angle Arc & Warning
            guidesHTML += `<line x1="${pts.hip[0]}" y1="${pts.hip[1]}" x2="${pts.hip[0]}" y2="${pts.hip[1] - 80}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="3,3"/>`;
            annotationsHTML += `
              <g>
                <text x="75" y="65" font-size="11" font-weight="800" fill="#ef4444">&#9888; 48° Forward Lean</text>
                <path d="M ${pts.hip[0]} ${pts.hip[1]-40} A 40 40 0 0 0 ${pts.hip[0]-25} ${pts.hip[1]-30}" fill="none" stroke="#ef4444" stroke-width="2"/>
              </g>
            `;
          } else {
            // Correct Upright Angle & Guide
            guidesHTML += `<line x1="${pts.hip[0]}" y1="${pts.hip[1]}" x2="${pts.hip[0]}" y2="${pts.hip[1] - 80}" stroke="#10b981" stroke-width="1.5" stroke-dasharray="3,3"/>`;
            annotationsHTML += `
              <g>
                <text x="175" y="70" font-size="11" font-weight="800" fill="#10b981">&#10003; 18° Upright Spine</text>
              </g>
            `;
          }
        } else if (this.flawType.includes("shallow")) {
          // Parallel Depth Guideline
          guidesHTML += `<line x1="80" y1="205" x2="260" y2="205" stroke="${isUser ? '#ef4444' : '#10b981'}" stroke-width="1.5" stroke-dasharray="4,4"/>`;
          if (isUser) {
            annotationsHTML += `<text x="85" y="198" font-size="11" font-weight="800" fill="#ef4444">&#9888; Stopped Above Parallel</text>`;
          } else {
            annotationsHTML += `<text x="85" y="198" font-size="11" font-weight="800" fill="#10b981">&#10003; Full Parallel Depth (90°)</text>`;
          }
        }
      }

    // 2. SQUAT KNEE VALGUS (Front View)
    } else if (this.exercise === "squat_knee_valgus") {
      const data = AnimatedSkeleton.KINEMATICS["squat_knee_valgus"];
      const startPose = data.standing;
      const bottomPose = isUser ? data.valgus_bottom_user : data.valgus_bottom_correct;
      const pts = this.interpolatePose(startPose, bottomPose, depthFactor);

      // Torso & Shoulders
      bonesHTML += `<line x1="${pts.shoulderL[0]}" y1="${pts.shoulderL[1]}" x2="${pts.shoulderR[0]}" y2="${pts.shoulderR[1]}" stroke="${normalColor}" stroke-width="4"/>`;
      bonesHTML += `<line x1="170" y1="${pts.neck[1]}" x2="170" y2="${pts.hipL[1]}" stroke="${normalColor}" stroke-width="4"/>`;
      bonesHTML += `<line x1="${pts.hipL[0]}" y1="${pts.hipL[1]}" x2="${pts.hipR[0]}" y2="${pts.hipR[1]}" stroke="${normalColor}" stroke-width="4"/>`;

      // Legs
      bonesHTML += `<line x1="${pts.hipL[0]}" y1="${pts.hipL[1]}" x2="${pts.kneeL[0]}" y2="${pts.kneeL[1]}" stroke="${highlightColor}" stroke-width="4.5"/>`;
      bonesHTML += `<line x1="${pts.kneeL[0]}" y1="${pts.kneeL[1]}" x2="${pts.ankleL[0]}" y2="${pts.ankleL[1]}" stroke="${highlightColor}" stroke-width="4"/>`;
      bonesHTML += `<line x1="${pts.hipR[0]}" y1="${pts.hipR[1]}" x2="${pts.kneeR[0]}" y2="${pts.kneeR[1]}" stroke="${highlightColor}" stroke-width="4.5"/>`;
      bonesHTML += `<line x1="${pts.kneeR[0]}" y1="${pts.kneeR[1]}" x2="${pts.ankleR[0]}" y2="${pts.ankleR[1]}" stroke="${highlightColor}" stroke-width="4"/>`;

      // Joints
      jointsHTML += `<circle cx="${pts.head[0]}" cy="${pts.head[1]}" r="13" fill="none" stroke="${normalColor}" stroke-width="3"/>`;
      jointsHTML += `<circle cx="${pts.kneeL[0]}" cy="${pts.kneeL[1]}" r="6" fill="${highlightColor}"/>`;
      jointsHTML += `<circle cx="${pts.kneeR[0]}" cy="${pts.kneeR[1]}" r="6" fill="${highlightColor}"/>`;

      if (depthFactor > 0.5) {
        if (isUser) {
          // Inward arrows on knees
          guidesHTML += `
            <g>
              <line x1="130" y1="205" x2="155" y2="205" stroke="#ef4444" stroke-width="2.5"/>
              <polygon points="152,201 160,205 152,209" fill="#ef4444"/>
              <line x1="210" y1="205" x2="185" y2="205" stroke="#ef4444" stroke-width="2.5"/>
              <polygon points="188,201 180,205 188,209" fill="#ef4444"/>
            </g>
          `;
          annotationsHTML += `<text x="95" y="165" font-size="11" font-weight="800" fill="#ef4444">&#9888; Knees Moving Inward</text>`;
        } else {
          // Outward alignment vectors
          guidesHTML += `
            <g>
              <line x1="130" y1="170" x2="130" y2="245" stroke="#10b981" stroke-width="1.5" stroke-dasharray="3,3"/>
              <line x1="210" y1="170" x2="210" y2="245" stroke="#10b981" stroke-width="1.5" stroke-dasharray="3,3"/>
            </g>
          `;
          annotationsHTML += `<text x="90" y="165" font-size="11" font-weight="800" fill="#10b981">&#10003; Knees Aligned Over Feet</text>`;
        }
      }

    // 3. PUSH-UP KINEMATICS
    } else if (this.exercise === "pushup") {
      const data = AnimatedSkeleton.KINEMATICS["pushup"];
      const startPose = data.plank_top;
      
      let bottomPose;
      if (this.flawType.includes("shallow")) {
        bottomPose = isUser ? data.shallow_bottom_user : data.shallow_bottom_correct;
      } else {
        bottomPose = isUser ? data.sag_bottom_user : data.sag_bottom_correct;
      }

      const pts = this.interpolatePose(startPose, bottomPose, depthFactor);
      const isSagFlaw = this.flawType.includes("sag");
      const spineColor = isSagFlaw ? highlightColor : normalColor;

      // Collinear Plank line: shoulder -> hip -> knee -> ankle
      bonesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.hip[0]}" y2="${pts.hip[1]}" stroke="${spineColor}" stroke-width="4.5" stroke-linecap="round"/>`;
      bonesHTML += `<line x1="${pts.hip[0]}" y1="${pts.hip[1]}" x2="${pts.knee[0]}" y2="${pts.knee[1]}" stroke="${spineColor}" stroke-width="4" stroke-linecap="round"/>`;
      bonesHTML += `<line x1="${pts.knee[0]}" y1="${pts.knee[1]}" x2="${pts.ankle[0]}" y2="${pts.ankle[1]}" stroke="${normalColor}" stroke-width="4" stroke-linecap="round"/>`;
      
      // Arms
      bonesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.elbow[0]}" y2="${pts.elbow[1]}" stroke="${normalColor}" stroke-width="3.5" stroke-linecap="round"/>`;
      bonesHTML += `<line x1="${pts.elbow[0]}" y1="${pts.elbow[1]}" x2="${pts.wrist[0]}" y2="${pts.wrist[1]}" stroke="${normalColor}" stroke-width="3" stroke-linecap="round"/>`;

      // Head & Joints
      jointsHTML += `<circle cx="${pts.head[0]}" cy="${pts.head[1]}" r="12" fill="none" stroke="${highlightColor}" stroke-width="3"/>`;
      ["shoulder", "elbow", "wrist", "hip", "knee", "ankle"].forEach(j => {
        const p = pts[j];
        const isHigh = (j === "hip" && isSagFlaw) || (j === "elbow");
        jointsHTML += `<circle cx="${p[0]}" cy="${p[1]}" r="${isHigh ? 6 : 4}" fill="${isHigh ? highlightColor : normalColor}"/>`;
        jointsHTML += `<circle cx="${p[0]}" cy="${p[1]}" r="2" fill="#ffffff"/>`;
      });

      if (depthFactor > 0.5) {
        if (isSagFlaw) {
          if (isUser) {
            guidesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.ankle[0]}" y2="${pts.ankle[1]}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="3,3"/>`;
            annotationsHTML += `<text x="135" y="145" font-size="11" font-weight="800" fill="#ef4444">&#9888; Hips Dropping (Sagging)</text>`;
          } else {
            guidesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.ankle[0]}" y2="${pts.ankle[1]}" stroke="#10b981" stroke-width="2"/>`;
            annotationsHTML += `<text x="135" y="145" font-size="11" font-weight="800" fill="#10b981">&#10003; Rigid Straight Plank Line</text>`;
          }
        } else if (this.flawType.includes("shallow")) {
          if (isUser) {
            annotationsHTML += `<text x="75" y="105" font-size="11" font-weight="800" fill="#ef4444">&#9888; Incomplete Depth</text>`;
          } else {
            annotationsHTML += `<text x="75" y="105" font-size="11" font-weight="800" fill="#10b981">&#10003; Full Depth (90° Elbows)</text>`;
          }
        }
      }

    // 4. YOGA POSTURE
    } else {
      const data = AnimatedSkeleton.KINEMATICS["yoga"];
      const targetPose = isUser ? data.bad : data.good;
      const pts = targetPose;

      bonesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.hip[0]}" y2="${pts.hip[1]}" stroke="${highlightColor}" stroke-width="4.5"/>`;
      bonesHTML += `<line x1="${pts.shoulder[0]}" y1="${pts.shoulder[1]}" x2="${pts.elbow[0]}" y2="${pts.elbow[1]}" stroke="${normalColor}" stroke-width="3.5"/>`;
      bonesHTML += `<line x1="${pts.elbow[0]}" y1="${pts.elbow[1]}" x2="${pts.wrist[0]}" y2="${pts.wrist[1]}" stroke="${normalColor}" stroke-width="3"/>`;
      bonesHTML += `<line x1="${pts.hip[0]}" y1="${pts.hip[1]}" x2="${pts.knee[0]}" y2="${pts.knee[1]}" stroke="${normalColor}" stroke-width="4.5"/>`;
      bonesHTML += `<line x1="${pts.knee[0]}" y1="${pts.knee[1]}" x2="${pts.ankle[0]}" y2="${pts.ankle[1]}" stroke="${normalColor}" stroke-width="4"/>`;

      jointsHTML += `<circle cx="${pts.head[0]}" cy="${pts.head[1]}" r="13" fill="none" stroke="${highlightColor}" stroke-width="3"/>`;
      annotationsHTML += `<text x="110" y="35" font-size="11" font-weight="800" fill="${highlightColor}">${isUser ? '&#9888; Detected Alignment' : '&#10003; Target Posture Alignment'}</text>`;
    }

    bonesG.innerHTML = bonesHTML;
    jointsG.innerHTML = jointsHTML;
    guidesG.innerHTML = guidesHTML;
    annotationsG.innerHTML = annotationsHTML;
  }
}

window.AnimatedSkeleton = AnimatedSkeleton;
