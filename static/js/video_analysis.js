/**
 * video_analysis.js
 * ApexMotion Video Analysis Controller.
 * Handles video file selection, API submission, animated skeletal human demonstration,
 * voice playback, and Today's Workout log integration.
 */

document.addEventListener("DOMContentLoaded", () => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("video-file-input");
  const selectedFileName = document.getElementById("selected-file-name");
  const sampleSelect = document.getElementById("sample-select");
  const btnLoadSample = document.getElementById("btn-load-sample");
  const uploadForm = document.getElementById("upload-form");
  const btnSubmit = document.getElementById("btn-submit-analysis");
  const processingIndicator = document.getElementById("processing-indicator");
  const processingStatusText = document.getElementById("processing-status-text");

  const resultsContainer = document.getElementById("results-container");
  const resultFilenameLabel = document.getElementById("result-filename-label");
  const resultOverallFormBadge = document.getElementById("result-overall-form-badge");
  const resVideoDurationLabel = document.getElementById("res-video-duration-label");

  const resExerciseDetected = document.getElementById("res-exercise-detected");
  const resTotalReps = document.getElementById("res-total-reps");
  const resGoodReps = document.getElementById("res-good-reps");
  const resBadReps = document.getElementById("res-bad-reps");

  const resultVideoPlayer = document.getElementById("result-video-player");
  const resIssuesList = document.getElementById("res-issues-list");
  const resAdjustmentsContainer = document.getElementById("res-adjustments-container");
  const resNextWorkoutText = document.getElementById("res-next-workout-text");

  const correctionWhatIsWrong = document.getElementById("correction-what-is-wrong");
  const correctionHowToCorrect = document.getElementById("correction-how-to-correct");
  const correctionWhyItMatters = document.getElementById("correction-why-it-matters");
  const btnPlayVoiceCue = document.getElementById("btn-play-voice-cue");
  const btnLogToHistory = document.getElementById("btn-log-to-history");

  let selectedSampleFile = null;
  let currentSkeletonInstance = null;
  let currentVoiceText = "";
  let currentSessionData = null;

  // 1. Drag and drop file selection
  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--accent-turquoise)";
    dropzone.style.backgroundColor = "var(--accent-turquoise-light)";
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.style.borderColor = "var(--border-medium)";
    dropzone.style.backgroundColor = "var(--bg-subtle)";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--border-medium)";
    dropzone.style.backgroundColor = "var(--bg-subtle)";
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected();
    }
  });

  fileInput.addEventListener("change", handleFileSelected);

  function handleFileSelected() {
    if (fileInput.files && fileInput.files[0]) {
      selectedSampleFile = null;
      sampleSelect.value = "";
      const file = fileInput.files[0];
      selectedFileName.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
      selectedFileName.style.display = "block";
    }
  }

  // 2. Load Sample Video
  btnLoadSample.addEventListener("click", () => {
    const val = sampleSelect.value;
    if (!val) {
      alert("Please select a sample video from the dropdown.");
      return;
    }
    selectedSampleFile = val;
    fileInput.value = "";
    selectedFileName.textContent = `Using repository demo: ${val}`;
    selectedFileName.style.display = "block";
  });

  // 3. Form Submit
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!fileInput.files[0] && !selectedSampleFile) {
      alert("Please choose a video file or pick a repository demo video.");
      return;
    }

    const formData = new FormData();
    const exerciseMode = document.getElementById("video-exercise-mode").value;
    formData.append("exercise_type", exerciseMode);

    if (fileInput.files[0]) {
      formData.append("video_file", fileInput.files[0]);
    } else if (selectedSampleFile) {
      formData.append("sample_filename", selectedSampleFile);
    }

    // UI Loading state
    btnSubmit.disabled = true;
    processingIndicator.style.display = "block";
    resultsContainer.style.display = "none";
    if (processingStatusText) {
      processingStatusText.textContent = fileInput.files[0] ? "Uploading and processing video..." : "Analyzing repository footage...";
    }

    try {
      const res = await fetch("/api/analyze_video", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Analysis failed");
      }

      const report = await res.json();
      currentSessionData = report;
      renderReport(report);

    } catch (err) {
      console.error(err);
      alert("Video analysis error: " + err.message);
    } finally {
      btnSubmit.disabled = false;
      processingIndicator.style.display = "none";
    }
  });

  // 4. Render Report & Animated Skeleton
  function renderReport(data) {
    resultsContainer.style.display = "block";

    resultFilenameLabel.textContent = `Analyzed: ${data.video_filename} (${data.processed_duration_seconds}s processing)`;
    if (resVideoDurationLabel) {
      resVideoDurationLabel.textContent = `Duration: ${data.video_duration || '00:00'}`;
    }

    resExerciseDetected.textContent = data.exercise_detected;
    resTotalReps.textContent = data.total_repetitions;
    resGoodReps.textContent = data.good_repetitions;
    resBadReps.textContent = data.correction_needed_repetitions;

    // Overall Form Badge
    const formPct = data.form_score_pct || 0;
    if (formPct >= 70) {
      resultOverallFormBadge.textContent = `GOOD FORM (${formPct}%)`;
      resultOverallFormBadge.className = "form-pill-display good";
    } else {
      resultOverallFormBadge.textContent = `NEEDS CORRECTION (${formPct}%)`;
      resultOverallFormBadge.className = "form-pill-display warn";
    }

    // Video Player
    const videoSrc = data.playable_video_url || data.output_video_url;
    if (videoSrc) {
      resultVideoPlayer.src = videoSrc;
      resultVideoPlayer.load();
      resultVideoPlayer.play().catch(() => {});
    }

    // Issues list
    resIssuesList.innerHTML = "";
    if (data.form_issues && data.form_issues.length > 0) {
      data.form_issues.forEach(issue => {
        const count = data.issue_counts ? data.issue_counts[issue] : null;
        const li = document.createElement("li");
        li.className = "feedback-item";
        li.innerHTML = `<span class="feedback-bullet">&bull;</span><span>${issue} ${count ? `(${count} occurrences)` : ''}</span>`;
        resIssuesList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.className = "feedback-item";
      li.innerHTML = `<span class="feedback-bullet" style="color: var(--status-good);">&check;</span><span>No severe biomechanical deviations detected.</span>`;
      resIssuesList.appendChild(li);
    }

    // Detailed Posture Correction Explanation
    const corr = data.detailed_correction || {};
    if (correctionWhatIsWrong) correctionWhatIsWrong.textContent = corr.what_is_wrong || "No significant issues detected.";
    if (correctionHowToCorrect) correctionHowToCorrect.textContent = corr.how_to_correct || "Maintain your steady movement rhythm.";
    if (correctionWhyItMatters) correctionWhyItMatters.textContent = corr.why_it_matters || "Proper alignment distributes joint stress evenly.";
    if (resNextWorkoutText) resNextWorkoutText.textContent = corr.suggested_next_workout || "Gradually increase volume next set.";

    currentVoiceText = corr.voice_instruction || "Maintain upright alignment.";

    // Mount & Launch Animated Human Skeleton Demo
    const skelMount = document.getElementById("animated-skeleton-mount");
    if (skelMount && window.AnimatedSkeleton) {
      currentSkeletonInstance = new window.AnimatedSkeleton("animated-skeleton-mount");
      const detectedExercise = (data.exercise_detected || corr.exercise || "squat").toLowerCase();
      currentSkeletonInstance.init(corr.visual_type || "squat_lean", detectedExercise);
    }

    // Training Adjustments
    resAdjustmentsContainer.innerHTML = "";
    if (data.training_adjustments && data.training_adjustments.length > 0) {
      data.training_adjustments.forEach(adj => {
        const card = document.createElement("div");
        card.className = "advice-card";
        card.textContent = adj;
        resAdjustmentsContainer.appendChild(card);
      });
    }

    // Automatic Voice Suggestion
    if (currentVoiceText) {
      speakVoice(currentVoiceText);
    }

    // Smooth Scroll
    resultsContainer.scrollIntoView({ behavior: "smooth" });
  }

  // 5. Voice Instruction Player Button
  btnPlayVoiceCue.addEventListener("click", () => {
    if (currentVoiceText) speakVoice(currentVoiceText);
  });

  function speakVoice(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.volume = 1.0;
    window.speechSynthesis.speak(utterance);
  }

  // 6. Log to Today's Workout History Button
  btnLogToHistory.addEventListener("click", () => {
    if (!currentSessionData || !window.HistoryManager) return;

    window.HistoryManager.addSession({
      exercise: currentSessionData.exercise_detected || "Squat",
      reps: currentSessionData.total_repetitions || 0,
      form: currentSessionData.form_quality || "Good",
      duration: currentSessionData.video_duration || "02:00",
      form_status: currentSessionData.form_quality || "Good",
      detected_issues: (currentSessionData.form_issues || []).join(", ") || (currentSessionData.detailed_correction ? currentSessionData.detailed_correction.detected_issue : ""),
      feedback: (currentSessionData.suggested_corrections || []).join("; ") || (currentSessionData.detailed_correction ? currentSessionData.detailed_correction.how_to_correct : "")
    });

    btnLogToHistory.textContent = "Saved to Your Log \u2713";
    btnLogToHistory.classList.add("btn-primary");
    btnLogToHistory.classList.remove("btn-secondary");
    btnLogToHistory.disabled = true;
  });
});
