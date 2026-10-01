/**
 * yoga_tracker.js
 * ApexMotion Yoga Trainer Controller.
 * Handles webcam stream, pose comparison, hold timer countdown,
 * animated alignment suggestions, audio cues, and workout logging.
 */

document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("camera-video");
  const overlayCanvas = document.getElementById("overlay-canvas");
  const captureCanvas = document.getElementById("capture-canvas");
  const ctx = overlayCanvas.getContext("2d");
  const captureCtx = captureCanvas.getContext("2d");

  const btnToggleCamera = document.getElementById("btn-toggle-camera");
  const btnResetHold = document.getElementById("btn-reset-hold");
  const yogaPoseSelect = document.getElementById("yoga-pose-select");
  const targetHoldSelect = document.getElementById("target-hold-select");
  const voiceToggle = document.getElementById("voice-toggle");

  const targetPoseTitle = document.getElementById("target-pose-title");
  const targetPoseDesc = document.getElementById("target-pose-desc");
  const targetPoseBadge = document.getElementById("target-pose-badge");

  const cameraPlaceholder = document.getElementById("camera-placeholder");
  const liveHudTop = document.getElementById("live-hud-top");
  const hudPosePill = document.getElementById("hud-pose-pill");
  const hudYogaStatus = document.getElementById("hud-yoga-status");

  const holdTimerDisplay = document.getElementById("hold-timer-display");
  const holdProgressFill = document.getElementById("hold-progress-fill");
  const bestHoldDisplay = document.getElementById("best-hold-display");
  const yogaStatusDisplay = document.getElementById("yoga-status-display");
  const yogaFeedbackList = document.getElementById("yoga-feedback-list");

  const correctionOverlay = document.getElementById("correction-overlay");
  const correctionArrow = document.getElementById("correction-arrow");
  const correctionText = document.getElementById("correction-text");

  let isStreaming = false;
  let mediaStream = null;
  let processIntervalId = null;
  let timerIntervalId = null;
  let elapsedSeconds = 0;
  let isProcessingFrame = false;
  let lastSpokenText = "";
  let lastSpokenTime = 0;
  let highestHold = 0;

  const POSE_INFO = {
    "tadasana": {
      "name": "Tadasana (Mountain Pose)",
      "badge": "Balance & Spine",
      "desc": "Standing tall with upright spine, arms relaxed alongside or extended, chest open, weight evenly balanced."
    },
    "tree": {
      "name": "Tree Pose (Vrikshasana)",
      "badge": "Single Leg Balance",
      "desc": "Standing strong on one leg while placing the sole of the opposite foot onto the inner thigh or calf."
    },
    "warrior2": {
      "name": "Warrior II (Virabhadrasana II)",
      "badge": "Hip & Leg Strength",
      "desc": "Wide stance with front knee bent at 90°, back leg straight, and both arms extended horizontally parallel to floor."
    },
    "downward_dog": {
      "name": "Downward Dog (Adho Mukha Svanasana)",
      "badge": "Inversion & Spine Length",
      "desc": "Inverted 'V' shape with hands and feet pressing into the floor, hips pushed up and back, arms straight."
    }
  };

  const POSE_CONNECTIONS = [
    [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
    [11, 23], [12, 24], [23, 24],
    [23, 25], [25, 27], [24, 26], [26, 28]
  ];

  btnToggleCamera.addEventListener("click", async () => {
    if (!isStreaming) {
      await startCamera();
    } else {
      stopCamera();
    }
  });

  async function startCamera() {
    btnToggleCamera.disabled = true;
    btnToggleCamera.textContent = "Connecting Camera...";

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });

      video.srcObject = mediaStream;
      await video.play();

      isStreaming = true;
      elapsedSeconds = 0;
      highestHold = 0;

      cameraPlaceholder.style.display = "none";
      liveHudTop.style.display = "flex";
      btnToggleCamera.textContent = "End Practice";
      btnToggleCamera.classList.remove("btn-primary");
      btnToggleCamera.classList.add("btn-danger");
      btnToggleCamera.disabled = false;

      resizeCanvases();
      window.addEventListener("resize", resizeCanvases);

      processIntervalId = setInterval(captureAndSendYogaFrame, 75);
      timerIntervalId = setInterval(() => { elapsedSeconds++; }, 1000);

      speakVoice("Starting yoga practice for " + POSE_INFO[yogaPoseSelect.value].name);
    } catch (err) {
      console.error(err);
      let errMsg = "Camera access error: " + err.message;
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        errMsg = "Camera permission was denied. Please allow camera access in your browser address bar.";
      }
      alert(errMsg);
      btnToggleCamera.disabled = false;
      btnToggleCamera.textContent = "Begin Practice";
    }
  }

  function stopCamera() {
    isStreaming = false;
    if (processIntervalId) clearInterval(processIntervalId);
    if (timerIntervalId) clearInterval(timerIntervalId);
    if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
    video.srcObject = null;
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    cameraPlaceholder.style.display = "block";
    liveHudTop.style.display = "none";
    correctionOverlay.style.display = "none";

    // Log to Today's Exercise table if held at least 3 seconds
    if (highestHold >= 3 && window.HistoryManager) {
      const mins = Math.floor(elapsedSeconds / 60);
      const secs = elapsedSeconds % 60;
      const durationStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      window.HistoryManager.addSession({
        exercise: POSE_INFO[yogaPoseSelect.value].name.split(" ")[0],
        reps: `${Math.round(highestHold)}s hold`,
        form: "Good",
        duration: durationStr,
        form_status: "Good",
        detected_issues: "",
        feedback: `Maintained target yoga posture for ${Math.round(highestHold)}s`
      });
    }

    btnToggleCamera.textContent = "Begin Practice";
    btnToggleCamera.classList.remove("btn-danger");
    btnToggleCamera.classList.add("btn-primary");
  }

  function resizeCanvases() {
    const rect = video.getBoundingClientRect();
    overlayCanvas.width = rect.width;
    overlayCanvas.height = rect.height;
    captureCanvas.width = 480;
    captureCanvas.height = 360;
  }

  async function captureAndSendYogaFrame() {
    if (!isStreaming || isProcessingFrame || video.readyState < 2) return;

    isProcessingFrame = true;
    try {
      captureCtx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
      const dataUrl = captureCanvas.toDataURL("image/jpeg", 0.7);

      const payload = {
        image: dataUrl,
        pose: yogaPoseSelect.value,
        target_hold: parseInt(targetHoldSelect.value)
      };

      const res = await fetch("/api/process_yoga_frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("API error");
      const data = await res.json();
      updateYogaUI(data);

    } catch (err) {
      console.warn("Yoga frame error:", err);
    } finally {
      isProcessingFrame = false;
    }
  }

  function updateYogaUI(data) {
    if (!data) return;

    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    if (data.body_detected && data.landmarks) {
      const isAligned = data.is_holding || data.status.includes("GOOD") || data.status.includes("HOLDING");
      drawSkeleton(data.landmarks, isAligned);
    }

    const duration = data.hold_duration || 0.0;
    const target = data.target_hold || 10;
    if (duration > highestHold) highestHold = duration;

    holdTimerDisplay.innerHTML = duration.toFixed(1) + '<span style="font-size: 1.25rem;">s</span>';
    bestHoldDisplay.textContent = (data.best_hold_duration || highestHold).toFixed(1) + "s";

    const pct = Math.min(100, (duration / target) * 100);
    holdProgressFill.style.width = pct + "%";

    const isGood = data.is_holding || data.hold_completed;
    yogaStatusDisplay.textContent = data.status;
    yogaStatusDisplay.className = "form-pill-display " + (isGood ? "good" : "warn");

    hudPosePill.textContent = (data.pose_name || "Yoga").toUpperCase();
    hudYogaStatus.textContent = data.status;
    hudYogaStatus.className = "hud-pill " + (isGood ? "status-good" : "status-correction");

    if (data.feedback && data.feedback.length > 0) {
      yogaFeedbackList.innerHTML = "";
      data.feedback.forEach(item => {
        const li = document.createElement("li");
        li.className = "feedback-item";
        li.innerHTML = `<span class="feedback-bullet">&bull;</span><span>${item}</span>`;
        yogaFeedbackList.appendChild(li);
      });
    }

    if (data.animated_cue) {
      correctionOverlay.style.display = "block";
      correctionText.textContent = data.animated_cue.text || "";
      const dir = data.animated_cue.direction || "up";
      if (dir === "down") correctionArrow.innerHTML = "&darr;";
      else if (dir === "up") correctionArrow.innerHTML = "&uarr;";
      else if (dir === "right") correctionArrow.innerHTML = "&rarr;";
      else correctionArrow.innerHTML = "&harr;";

      correctionArrow.style.color = isGood ? "#10b981" : "#ef4444";
    } else {
      correctionOverlay.style.display = "none";
    }

    if (data.tts_prompt) {
      speakVoice(data.tts_prompt);
    }
  }

  function drawSkeleton(landmarks, isAligned) {
    const w = overlayCanvas.width;
    const h = overlayCanvas.height;

    const lmMap = {};
    landmarks.forEach(lm => {
      lmMap[lm.id] = { x: lm.x * w, y: lm.y * h, v: lm.v };
    });

    ctx.lineWidth = 3;
    ctx.strokeStyle = isAligned ? "rgba(240, 240, 240, 0.9)" : "rgba(239, 68, 68, 0.8)";
    ctx.lineCap = "round";

    POSE_CONNECTIONS.forEach(([start, end]) => {
      const p1 = lmMap[start];
      const p2 = lmMap[end];
      if (p1 && p2 && p1.v > 0.4 && p2.v > 0.4) {
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    });

    const keyJoints = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];
    keyJoints.forEach(id => {
      const pt = lmMap[id];
      if (pt && pt.v > 0.4) {
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 6, 0, 2 * Math.PI);
        ctx.fillStyle = isAligned ? "#10b981" : "#ef4444";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 2.5, 0, 2 * Math.PI);
        ctx.fillStyle = "#ffffff";
        ctx.fill();
      }
    });
  }

  function speakVoice(text) {
    if (!voiceToggle.checked) return;
    if (!('speechSynthesis' in window)) return;
    if (!text) return;

    const now = Date.now();
    if (text === lastSpokenText && (now - lastSpokenTime) < 4000) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.volume = 1.0;
    window.speechSynthesis.speak(utterance);

    lastSpokenText = text;
    lastSpokenTime = now;
  }

  yogaPoseSelect.addEventListener("change", async () => {
    const val = yogaPoseSelect.value;
    const info = POSE_INFO[val];
    if (info) {
      targetPoseTitle.textContent = info.name;
      targetPoseBadge.textContent = info.badge;
      targetPoseDesc.textContent = info.desc;
    }
    await fetch("/api/reset_yoga", { method: "POST" });
    holdTimerDisplay.innerHTML = '0.0<span style="font-size: 1.25rem;">s</span>';
    holdProgressFill.style.width = "0%";
    highestHold = 0;
    speakVoice("Switched to " + info.name);
  });

  btnResetHold.addEventListener("click", async () => {
    await fetch("/api/reset_yoga", { method: "POST" });
    holdTimerDisplay.innerHTML = '0.0<span style="font-size: 1.25rem;">s</span>';
    holdProgressFill.style.width = "0%";
    highestHold = 0;
    speakVoice("Timer reset.");
  });
});
