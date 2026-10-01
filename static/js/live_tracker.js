/**
 * live_tracker.js
 * ApexMotion Live Camera Workout Controller.
 * Handles webcam stream, skeleton canvas drawing, rep counting,
 * animated posture correction widget, audio coaching, and workout logging.
 */

document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("camera-video");
  const overlayCanvas = document.getElementById("overlay-canvas");
  const captureCanvas = document.getElementById("capture-canvas");
  const ctx = overlayCanvas.getContext("2d");
  const captureCtx = captureCanvas.getContext("2d");

  const btnToggleCamera = document.getElementById("btn-toggle-camera");
  const btnReset = document.getElementById("btn-reset");
  const btnFinish = document.getElementById("btn-finish");
  const exerciseSelect = document.getElementById("exercise-select");
  const voiceToggle = document.getElementById("voice-toggle");

  const cameraPlaceholder = document.getElementById("camera-placeholder");
  const liveHudTop = document.getElementById("live-hud-top");
  const hudExercisePill = document.getElementById("hud-exercise-pill");
  const hudFormPill = document.getElementById("hud-form-pill");

  const repDisplay = document.getElementById("rep-display");
  const goodRepsCount = document.getElementById("good-reps-count");
  const badRepsCount = document.getElementById("bad-reps-count");
  const formDisplay = document.getElementById("form-display");
  const feedbackList = document.getElementById("feedback-list");

  const correctionOverlay = document.getElementById("correction-overlay");
  const correctionArrow = document.getElementById("correction-arrow");
  const correctionText = document.getElementById("correction-text");

  let isStreaming = false;
  let mediaStream = null;
  let processIntervalId = null;
  let timerIntervalId = null;
  let workoutStartTime = null;
  let elapsedSeconds = 0;
  let isProcessingFrame = false;
  let lastSpokenText = "";
  let lastSpokenTime = 0;
  let latestAnalysisData = null;

  const POSE_CONNECTIONS = [
    [11, 12],
    [11, 13], [13, 15],
    [12, 14], [14, 16],
    [11, 23], [12, 24],
    [23, 24],
    [23, 25], [25, 27],
    [24, 26], [26, 28]
  ];

  // 1. Camera Toggle
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
      workoutStartTime = Date.now();
      elapsedSeconds = 0;

      cameraPlaceholder.style.display = "none";
      liveHudTop.style.display = "flex";
      btnToggleCamera.textContent = "Stop Workout";
      btnToggleCamera.classList.remove("btn-primary");
      btnToggleCamera.classList.add("btn-danger");
      btnToggleCamera.disabled = false;
      btnReset.disabled = false;
      btnFinish.disabled = false;

      resizeCanvases();
      window.addEventListener("resize", resizeCanvases);

      processIntervalId = setInterval(captureAndSendFrame, 65);
      timerIntervalId = setInterval(() => {
        elapsedSeconds++;
      }, 1000);

      speakVoice("Starting workout session. Position your body in the frame.");
    } catch (err) {
      console.error("Camera access error:", err);
      let errMsg = "Camera access error: " + err.message;
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        errMsg = "Camera permission was denied. Please allow camera access in your browser address bar to use live tracking.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        errMsg = "No camera was detected on this device. Please connect a webcam.";
      }
      alert(errMsg);
      btnToggleCamera.disabled = false;
      btnToggleCamera.textContent = "Start Workout";
    }
  }

  function stopCamera() {
    isStreaming = false;
    if (processIntervalId) clearInterval(processIntervalId);
    if (timerIntervalId) clearInterval(timerIntervalId);
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
    }
    video.srcObject = null;
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    cameraPlaceholder.style.display = "block";
    liveHudTop.style.display = "none";
    correctionOverlay.style.display = "none";

    btnToggleCamera.textContent = "Start Workout";
    btnToggleCamera.classList.remove("btn-danger");
    btnToggleCamera.classList.add("btn-primary");
    btnReset.disabled = true;
  }

  function resizeCanvases() {
    const rect = video.getBoundingClientRect();
    overlayCanvas.width = rect.width;
    overlayCanvas.height = rect.height;
    captureCanvas.width = 480;
    captureCanvas.height = 360;
  }

  // 2. Frame processing loop
  async function captureAndSendFrame() {
    if (!isStreaming || isProcessingFrame || video.readyState < 2) return;

    isProcessingFrame = true;
    try {
      captureCtx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
      const dataUrl = captureCanvas.toDataURL("image/jpeg", 0.7);

      const payload = {
        image: dataUrl,
        exercise: exerciseSelect.value
      };

      const res = await fetch("/api/process_frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("API response error");
      const data = await res.json();
      latestAnalysisData = data;
      updateUI(data);

    } catch (err) {
      console.warn("Frame process warning:", err);
    } finally {
      isProcessingFrame = false;
    }
  }

  // 3. UI Update & Skeleton Rendering
  function updateUI(data) {
    if (!data) return;

    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    if (data.body_detected && data.landmarks) {
      drawSkeleton(data.landmarks, data.form_status === "GOOD FORM");
    }

    repDisplay.textContent = data.reps;
    goodRepsCount.textContent = data.good_reps || 0;
    badRepsCount.textContent = data.bad_reps || 0;

    const isGood = data.form_status === "GOOD FORM";
    formDisplay.textContent = data.form_status;
    formDisplay.className = "form-pill-display " + (isGood ? "good" : "warn");

    const activeEx = data.exercise ? data.exercise.toUpperCase() : "TRACKING";
    hudExercisePill.textContent = "EXERCISE: " + activeEx;
    hudFormPill.textContent = data.form_status;
    hudFormPill.className = "hud-pill " + (isGood ? "status-good" : "status-correction");

    if (data.feedback && data.feedback.length > 0) {
      feedbackList.innerHTML = "";
      data.feedback.forEach(item => {
        const li = document.createElement("li");
        li.className = "feedback-item";
        li.innerHTML = `<span class="feedback-bullet">&bull;</span><span>${item}</span>`;
        feedbackList.appendChild(li);
      });
    }

    if (data.animated_cue) {
      correctionOverlay.style.display = "block";
      correctionText.textContent = data.animated_cue.text || "";
      const dir = data.animated_cue.direction || "down";
      if (dir === "down") correctionArrow.innerHTML = "&darr;";
      else if (dir === "up") correctionArrow.innerHTML = "&uarr;";
      else if (dir === "right") correctionArrow.innerHTML = "&rarr;";
      else if (dir === "inward") correctionArrow.innerHTML = "&harr;";
      else correctionArrow.innerHTML = "&check;";

      correctionArrow.style.color = data.animated_cue.type === "check" ? "#10b981" : "#ef4444";
    } else {
      correctionOverlay.style.display = "none";
    }

    if (data.tts_prompt) {
      speakVoice(data.tts_prompt);
    }
  }

  function drawSkeleton(landmarks, isGoodForm) {
    const w = overlayCanvas.width;
    const h = overlayCanvas.height;

    const lmMap = {};
    landmarks.forEach(lm => {
      lmMap[lm.id] = { x: lm.x * w, y: lm.y * h, v: lm.v };
    });

    ctx.lineWidth = 3;
    ctx.strokeStyle = isGoodForm ? "rgba(240, 240, 240, 0.85)" : "rgba(239, 68, 68, 0.8)";
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
        ctx.fillStyle = isGoodForm ? "#10b981" : "#ef4444";
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
    utterance.rate = 1.05;
    utterance.volume = 1.0;
    window.speechSynthesis.speak(utterance);

    lastSpokenText = text;
    lastSpokenTime = now;
  }

  // 4. Reset & Finish Workout Handlers
  btnReset.addEventListener("click", async () => {
    try {
      await fetch("/api/reset_exercise", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ exercise: exerciseSelect.value })
      });
      repDisplay.textContent = "0";
      goodRepsCount.textContent = "0";
      badRepsCount.textContent = "0";
      speakVoice("Counter reset.");
    } catch (e) {
      console.error(e);
    }
  });

  btnFinish.addEventListener("click", async () => {
    try {
      const totalReps = parseInt(repDisplay.textContent) || 0;
      const goodReps = parseInt(goodRepsCount.textContent) || 0;
      const formQuality = (goodReps / Math.max(totalReps, 1)) >= 0.7 ? "Good" : "Needs Improvement";

      const mins = Math.floor(elapsedSeconds / 60);
      const secs = elapsedSeconds % 60;
      const durationStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

      // 1. Add to Today's Exercise table
      if (window.HistoryManager) {
        await window.HistoryManager.addSession({
          exercise: exerciseSelect.options[exerciseSelect.selectedIndex].text,
          reps: totalReps,
          form: formQuality,
          duration: durationStr,
          form_status: formQuality,
          detected_issues: (totalReps > goodReps) ? "Form deviation detected during reps" : "",
          feedback: formQuality === "Good" ? "Maintained solid biomechanics" : "Focus on chest upright and depth"
        });
      }

      // 2. Save session summary
      const res = await fetch("/api/save_summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          voice_enabled: voiceToggle.checked,
          duration_seconds: elapsedSeconds
        })
      });
      const data = await res.json();
      if (data.redirect) {
        stopCamera();
        window.location.href = data.redirect;
      }
    } catch (e) {
      console.error(e);
    }
  });

  exerciseSelect.addEventListener("change", async () => {
    await fetch("/api/reset_exercise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exercise: exerciseSelect.value })
    });
    speakVoice("Switched to " + exerciseSelect.options[exerciseSelect.selectedIndex].text);
  });
});
