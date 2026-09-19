// ExamPlan AI - Client Application Logic

const state = {
  currentDocId: null,
  currentPlanId: null,
  currentPlanData: null,
  activeView: "todo",
  stagedFiles: [], // List of selected files before analysis
  timetableMode: "uniform", // uniform | weekly | upload
  weeklySchedule: null,
  geminiApiKey: localStorage.getItem("examplan_gemini_key") || "",
  activeFiles: [],
  uploadedFileObjects: [],
  currentDocTopics: [],
  googleClientId: "",
  currentUser: null,
  authToken: localStorage.getItem("examplan_auth_token") || "",
  targetGoal: "advanced", // "basic" (Pass môn) | "advanced" (Điểm giỏi)
  activeStudyTask: null,
  studyLessonCache: {}, // taskId_goal -> lessonData
  activeSlideIndex: 0,
  activeSlideImages: [],
  slideViewMode: "carousel" // "carousel" | "scroll"
};

// --- DOM Elements ---
// Target Goal Filter DOM elements
const goalFilterBasic = document.getElementById("goal-filter-basic");
const goalFilterAdvanced = document.getElementById("goal-filter-advanced");

// Study Modal DOM elements
const studyModal = document.getElementById("study-modal");
const btnCloseStudyModal = document.getElementById("btn-close-study-modal");
const btnStudyModalCloseFooter = document.getElementById("btn-study-modal-close-footer");
const btnStudyModalToggleDone = document.getElementById("btn-study-modal-toggle-done");
const studyModalBadgeType = document.getElementById("study-modal-badge-type");
const studyModalBadgeDiff = document.getElementById("study-modal-badge-diff");
const studyModalTime = document.getElementById("study-modal-time");
const studyModalTitle = document.getElementById("study-modal-title");
const studyModalTopic = document.getElementById("study-modal-topic");
const studyModalLoading = document.getElementById("study-modal-loading");
const studyModalBody = document.getElementById("study-modal-body");
const studyModalConceptsList = document.getElementById("study-modal-concepts-list");
const studyQuizQuestion = document.getElementById("study-quiz-question");
const studyQuizOptions = document.getElementById("study-quiz-options");
const studyQuizFeedback = document.getElementById("study-quiz-feedback");
const studyModalAdvancedSection = document.getElementById("study-modal-advanced-section");
const studyModalAdvancedList = document.getElementById("study-modal-advanced-list");

// Slide Viewer DOM elements (Auto-loaded from static library)
const studyModalSlidesSection = document.getElementById("study-modal-slides-section");
const studySlideCountBadge = document.getElementById("study-slide-count-badge");
const btnSlideModeCarousel = document.getElementById("btn-slide-mode-carousel");
const btnSlideModeScroll = document.getElementById("btn-slide-mode-scroll");
const studySlideCarouselContainer = document.getElementById("study-slide-carousel-container");
const studySlideCarouselImg = document.getElementById("study-slide-carousel-img");
const btnSlidePrev = document.getElementById("btn-slide-prev");
const btnSlideNext = document.getElementById("btn-slide-next");
const studySlidePageIndicator = document.getElementById("study-slide-page-indicator");
const studySlideDots = document.getElementById("study-slide-dots");
const btnSlideFullscreen = document.getElementById("btn-slide-fullscreen");
const studySlideScrollContainer = document.getElementById("study-slide-scroll-container");

// Study Modal Tabs & In-Modal Q&A DOM elements
const tabStudyLessonBtn = document.getElementById("tab-study-lesson-btn");
const tabStudyQaBtn = document.getElementById("tab-study-qa-btn");
const studyModalQaPane = document.getElementById("study-modal-qa-pane");
const studyQaMessages = document.getElementById("study-qa-messages");
const studyQaForm = document.getElementById("study-qa-form");
const studyQaInput = document.getElementById("study-qa-input");
const btnStudyQaSend = document.getElementById("btn-study-qa-send");

// Auth & User DOM elements
const btnOpenLogin = document.getElementById("btn-open-login");
const userProfileWidget = document.getElementById("user-profile-widget");
const btnUserMenu = document.getElementById("btn-user-menu");
const userDropdownMenu = document.getElementById("user-dropdown-menu");
const userAvatar = document.getElementById("user-avatar");
const userDisplayName = document.getElementById("user-display-name");
const userProviderBadge = document.getElementById("user-provider-badge");
const userDropdownEmail = document.getElementById("user-dropdown-email");
const btnOpenLibrary = document.getElementById("btn-open-library");
const btnSwitchAccount = document.getElementById("btn-switch-account");
const btnLogout = document.getElementById("btn-logout");
const authModal = document.getElementById("auth-modal");
const btnCloseAuth = document.getElementById("btn-close-auth");
const btnLoginGoogle = document.getElementById("btn-login-google");
const btnLoginFacebook = document.getElementById("btn-login-facebook");
const btnLoginGuest = document.getElementById("btn-login-guest");
const libraryModal = document.getElementById("library-modal");
const btnCloseLibrary = document.getElementById("btn-close-library");
const libraryItemsList = document.getElementById("library-items-list");
const docStorageBadge = document.getElementById("doc-storage-badge");

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const tabFileBtn = document.getElementById("tab-file-btn");
const tabUrlBtn = document.getElementById("tab-url-btn");
const uploadFilePane = document.getElementById("upload-file-pane");
const uploadUrlPane = document.getElementById("upload-url-pane");
const urlInput = document.getElementById("url-input");
const btnSubmitUrl = document.getElementById("btn-submit-url");
const analysisLoading = document.getElementById("analysis-loading");
const docResultCard = document.getElementById("document-result-card");
const docSubjectTitle = document.getElementById("doc-subject-title");
const docSummary = document.getElementById("doc-summary");
const topicsPreviewList = document.getElementById("topics-preview-list");
const planForm = document.getElementById("plan-form");
const btnGeneratePlan = document.getElementById("btn-generate-plan");
const examDateInput = document.getElementById("exam-date-input");
const dailyHoursSlider = document.getElementById("daily-hours-slider");
const hoursDisplay = document.getElementById("hours-display");
const btnLoadSample = document.getElementById("btn-load-sample");

// Timetable DOM elements
const ttModeUniform = document.getElementById("tt-mode-uniform");
const ttModeWeekly = document.getElementById("tt-mode-weekly");
const ttModeUpload = document.getElementById("tt-mode-upload");
const ttPanelUniform = document.getElementById("tt-panel-uniform");
const ttPanelWeekly = document.getElementById("tt-panel-weekly");
const ttPanelUpload = document.getElementById("tt-panel-upload");
const ttDropZone = document.getElementById("tt-drop-zone");
const ttFileInput = document.getElementById("tt-file-input");
const ttUploadStatus = document.getElementById("tt-upload-status");
const ttStatusText = document.getElementById("tt-status-text");

// Active Files DOM elements
const activeFilesContainer = document.getElementById("active-files-container");
const activeFilesList = document.getElementById("active-files-list");
const activeFilesCount = document.getElementById("active-files-count");

// Staged Files DOM elements
const selectedFilesContainer = document.getElementById("selected-files-container");
const selectedFilesList = document.getElementById("selected-files-list");
const stagedCount = document.getElementById("staged-count");
const btnStartAnalysis = document.getElementById("btn-start-analysis");
const btnAnalysisText = document.getElementById("btn-analysis-text");
const btnClearAllStaged = document.getElementById("btn-clear-all-staged");

const setupSection = document.getElementById("setup-section");
const planDashboard = document.getElementById("plan-dashboard");
const dashSubjectBadge = document.getElementById("dash-subject-badge");
const dashTargetBadge = document.getElementById("dash-target-badge");
const dashPlanTitle = document.getElementById("dash-plan-title");
const dashDaysLeft = document.getElementById("dash-days-left");
const dashProgressPct = document.getElementById("dash-progress-pct");
const dashProgressBar = document.getElementById("dash-progress-bar");
const dashTasksDone = document.getElementById("dash-tasks-done");
const dashTasksTotal = document.getElementById("dash-tasks-total");
const btnReschedule = document.getElementById("btn-reschedule");
const btnExportIcal = document.getElementById("btn-export-ical");
const btnChangePlan = document.getElementById("btn-change-plan");

// Views
const viewTodoBtn = document.getElementById("view-todo-btn");
const viewCalendarBtn = document.getElementById("view-calendar-btn");
const viewKanbanBtn = document.getElementById("view-kanban-btn");
const viewTodoContent = document.getElementById("view-todo-content");
const viewCalendarContent = document.getElementById("view-calendar-content");
const viewKanbanContent = document.getElementById("view-kanban-content");
const calendarGrid = document.getElementById("calendar-grid");

// Kanban lists
const kanbanTodoList = document.getElementById("kanban-todo-list");
const kanbanReviewList = document.getElementById("kanban-review-list");
const kanbanDoneList = document.getElementById("kanban-done-list");
const kanbanTodoCount = document.getElementById("kanban-todo-count");
const kanbanReviewCount = document.getElementById("kanban-review-count");
const kanbanDoneCount = document.getElementById("kanban-done-count");

// Chat
const chatWidget = document.getElementById("chat-widget");
const chatWindow = document.getElementById("chat-window");
const btnToggleChat = document.getElementById("btn-toggle-chat");
const btnCloseChat = document.getElementById("btn-close-chat");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

// Settings
const btnOpenSettings = document.getElementById("btn-open-settings");
const btnCloseSettings = document.getElementById("btn-close-settings");
const btnSaveSettings = document.getElementById("btn-save-settings");
const settingsModal = document.getElementById("settings-modal");
const settingsApiKey = document.getElementById("settings-api-key");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {

  // --- Auth Event Listeners ---
  initAuth();

  if (btnOpenLogin) {
    btnOpenLogin.addEventListener("click", () => {
      if (authModal) authModal.classList.remove("hidden");
      initGoogleAuth();
    });
  }

  if (btnCloseAuth) {
    btnCloseAuth.addEventListener("click", () => {
      if (authModal) authModal.classList.add("hidden");
    });
  }

  if (btnUserMenu) {
    btnUserMenu.addEventListener("click", (e) => {
      e.stopPropagation();
      if (userDropdownMenu) userDropdownMenu.classList.toggle("hidden");
    });
  }

  document.addEventListener("click", (e) => {
    if (userDropdownMenu && !userDropdownMenu.contains(e.target) && !btnUserMenu.contains(e.target)) {
      userDropdownMenu.classList.add("hidden");
    }
  });

  if (btnLoginGoogle) {
    btnLoginGoogle.addEventListener("click", handleGoogleLogin);
  }

  if (btnLoginFacebook) {
    btnLoginFacebook.addEventListener("click", handleFacebookLogin);
  }

  if (btnLoginGuest) {
    btnLoginGuest.addEventListener("click", () => loginAsGuest(true));
  }

  if (btnSwitchAccount) {
    btnSwitchAccount.addEventListener("click", () => {
      if (userDropdownMenu) userDropdownMenu.classList.add("hidden");
      if (authModal) authModal.classList.remove("hidden");
    });
  }

  if (btnLogout) {
    btnLogout.addEventListener("click", handleLogout);
  }

  if (btnOpenLibrary) {
    btnOpenLibrary.addEventListener("click", openLibraryModal);
  }

  if (btnCloseLibrary) {
    btnCloseLibrary.addEventListener("click", () => {
      if (libraryModal) libraryModal.classList.add("hidden");
    });
  }

  // --- Target Goal Filter Listeners ---
  if (goalFilterBasic) {
    goalFilterBasic.addEventListener("click", () => setTargetGoal("basic"));
  }
  if (goalFilterAdvanced) {
    goalFilterAdvanced.addEventListener("click", () => setTargetGoal("advanced"));
  }

  // --- Study Lesson Modal Listeners ---
  if (btnCloseStudyModal) {
    btnCloseStudyModal.addEventListener("click", closeStudyModal);
  }
  if (btnStudyModalCloseFooter) {
    btnStudyModalCloseFooter.addEventListener("click", closeStudyModal);
  }
  if (btnStudyModalToggleDone) {
    btnStudyModalToggleDone.addEventListener("click", () => {
      if (state.activeStudyTask) {
        handleToggleTask(state.activeStudyTask.id);
        // Toggle visual state inside modal
        state.activeStudyTask.is_completed = !state.activeStudyTask.is_completed;
        updateStudyModalDoneButton(state.activeStudyTask.is_completed);
      }
    });
  }
  if (studyModal) {
    studyModal.addEventListener("click", (e) => {
      if (e.target === studyModal) closeStudyModal();
    });
  }

  // In-Modal Tabs switching
  if (tabStudyLessonBtn) {
    tabStudyLessonBtn.addEventListener("click", () => switchStudyModalTab("lesson"));
  }
  if (tabStudyQaBtn) {
    tabStudyQaBtn.addEventListener("click", () => switchStudyModalTab("qa"));
  }

  // In-Modal Q&A Form
  if (studyQaForm) {
    studyQaForm.addEventListener("submit", handleStudyQaSubmit);
  }

  // In-Modal Quick Prompts
  document.querySelectorAll(".btn-task-qa-prompt").forEach((b) => {
    b.addEventListener("click", () => {
      if (studyQaInput) {
        studyQaInput.value = b.textContent.trim().replace(/^[^\w\s]+/, "").trim();
        handleStudyQaSubmit(new Event("submit"));
      }
    });
  });

  // Slide Viewer Listeners
  if (btnSlidePrev) btnSlidePrev.addEventListener("click", prevSlide);
  if (btnSlideNext) btnSlideNext.addEventListener("click", nextSlide);
  if (btnSlideModeCarousel) btnSlideModeCarousel.addEventListener("click", () => switchSlideMode("carousel"));
  if (btnSlideModeScroll) btnSlideModeScroll.addEventListener("click", () => switchSlideMode("scroll"));

  // Set default exam date to +14 days
  const defaultDate = new Date();
  defaultDate.setDate(defaultDate.getDate() + 14);
  examDateInput.value = defaultDate.toISOString().split("T")[0];
  examDateInput.min = new Date().toISOString().split("T")[0];

  if (state.geminiApiKey) {
    settingsApiKey.value = state.geminiApiKey;
  }

  lucide.createIcons();
  bindEvents();
});

function bindEvents() {
  // Tabs for Upload
  tabFileBtn.addEventListener("click", () => {
    tabFileBtn.classList.add("border-indigo-600", "text-indigo-600");
    tabFileBtn.classList.remove("border-transparent", "text-slate-500");
    tabUrlBtn.classList.remove("border-indigo-600", "text-indigo-600");
    tabUrlBtn.classList.add("border-transparent", "text-slate-500");
    uploadFilePane.classList.remove("hidden");
    uploadUrlPane.classList.add("hidden");
  });

  tabUrlBtn.addEventListener("click", () => {
    tabUrlBtn.classList.add("border-indigo-600", "text-indigo-600");
    tabUrlBtn.classList.remove("border-transparent", "text-slate-500");
    tabFileBtn.classList.remove("border-indigo-600", "text-indigo-600");
    tabFileBtn.classList.add("border-transparent", "text-slate-500");
    uploadUrlPane.classList.remove("hidden");
    uploadFilePane.classList.add("hidden");
  });

  // Drag & drop
  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-indigo-500", "bg-indigo-50/50");
  });
  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-indigo-500", "bg-indigo-50/50");
  });
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-indigo-500", "bg-indigo-50/50");
    if (e.dataTransfer.files.length) {
      addStagedFiles(e.dataTransfer.files);
    }
  });
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) {
      addStagedFiles(e.target.files);
    }
  });

  // Staged Files handlers
  if (btnStartAnalysis) {
    btnStartAnalysis.addEventListener("click", () => {
      if (state.stagedFiles.length > 0) {
        handleFileUpload(state.stagedFiles);
      } else {
        alert("Vui lòng chọn ít nhất 1 tệp đề cương!");
      }
    });
  }

  if (btnClearAllStaged) {
    btnClearAllStaged.addEventListener("click", () => {
      state.stagedFiles = [];
      renderSelectedFiles();
      fileInput.value = "";
    });
  }

  // Delete Document Button
  const btnDeleteDoc = document.getElementById("btn-delete-doc");
  if (btnDeleteDoc) {
    btnDeleteDoc.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!state.currentDocId) return;
      if (!confirm("Bạn có chắc chắn muốn xóa tài liệu này không?")) return;

      try {
        const res = await fetch(`/api/documents/${state.currentDocId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Không thể xóa tài liệu.");

        state.currentDocId = null;
        state.currentPlanId = null;
        state.currentPlanData = null;
        docResultCard.classList.add("hidden");
        planDashboard.classList.add("hidden");
        fileInput.value = "";
        btnGeneratePlan.disabled = true;
        btnGeneratePlan.className = "w-full py-3.5 px-4 rounded-xl text-white font-bold bg-slate-400 cursor-not-allowed transition-all flex items-center justify-center gap-2";
        btnGeneratePlan.innerHTML = `<i data-lucide="zap" class="w-5 h-5"></i> <span>Vui lòng tải đề cương trước</span>`;
        lucide.createIcons();
        alert("🗑️ Đã xóa tài liệu thành công!");
      } catch (err) {
        alert("Lỗi khi xóa tài liệu: " + err.message);
      }
    });
  }

  // URL upload
  btnSubmitUrl.addEventListener("click", handleUrlUpload);

  // Load 1-Click Sample
  btnLoadSample.addEventListener("click", handleLoadSample);

  // Slider
  dailyHoursSlider.addEventListener("input", (e) => {
    const hrs = parseFloat(e.target.value);
    hoursDisplay.textContent = `${hrs.toFixed(1)} giờ / ngày (${Math.round(hrs * 60)} phút)`;
  });

  // Timetable Mode Switcher
  function setTimetableMode(mode) {
    state.timetableMode = mode;
    [ttModeUniform, ttModeWeekly, ttModeUpload].forEach((b) => {
      b.className = "flex-1 py-1.5 rounded-lg hover:text-slate-900 text-center";
    });
    ttPanelUniform.classList.add("hidden");
    ttPanelWeekly.classList.add("hidden");
    ttPanelUpload.classList.add("hidden");

    if (mode === "uniform") {
      ttModeUniform.className = "flex-1 py-1.5 rounded-lg bg-white text-indigo-600 shadow-sm text-center font-bold";
      ttPanelUniform.classList.remove("hidden");
    } else if (mode === "weekly") {
      ttModeWeekly.className = "flex-1 py-1.5 rounded-lg bg-white text-indigo-600 shadow-sm text-center font-bold";
      ttPanelWeekly.classList.remove("hidden");
    } else if (mode === "upload") {
      ttModeUpload.className = "flex-1 py-1.5 rounded-lg bg-white text-indigo-600 shadow-sm text-center font-bold";
      ttPanelUpload.classList.remove("hidden");
    }
  }

  ttModeUniform.addEventListener("click", () => setTimetableMode("uniform"));
  ttModeWeekly.addEventListener("click", () => setTimetableMode("weekly"));
  ttModeUpload.addEventListener("click", () => setTimetableMode("upload"));

  // Timetable File Upload
  ttDropZone.addEventListener("click", () => ttFileInput.click());
  ttFileInput.addEventListener("change", async (e) => {
    if (e.target.files.length) {
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append("file", file);
      if (state.geminiApiKey) formData.append("gemini_api_key", state.geminiApiKey);

      ttStatusText.textContent = "AI đang đọc và phân tích ca học bận...";
      ttUploadStatus.classList.remove("hidden");

      try {
        const res = await fetch("/api/timetable/upload", { method: "POST", body: formData });
        if (!res.ok) throw new Error("Không thể phân tích thời khóa biểu.");
        const data = await res.json();
        if (data.weekly_schedule) {
          document.getElementById("wh-mon").value = data.weekly_schedule.mon || 1.0;
          document.getElementById("wh-tue").value = data.weekly_schedule.tue || 1.0;
          document.getElementById("wh-wed").value = data.weekly_schedule.wed || 1.0;
          document.getElementById("wh-thu").value = data.weekly_schedule.thu || 1.0;
          document.getElementById("wh-fri").value = data.weekly_schedule.fri || 1.0;
          document.getElementById("wh-sat").value = data.weekly_schedule.sat || 2.0;
          document.getElementById("wh-sun").value = data.weekly_schedule.sun || 0.0;
          state.weeklySchedule = data.weekly_schedule;
          setTimetableMode("weekly");
          ttStatusText.textContent = "✓ " + (data.summary || "Đã áp dụng lịch rảnh theo TKB!");
          alert("✨ AI đã phân tích TKB trường của bạn: " + (data.summary || "Đã phân bổ lịch rảnh!"));
        }
      } catch (err) {
        alert("Lỗi: " + err.message);
      }
    }
  });

  // Score Target Cards Selection
  const scoreCards = document.querySelectorAll(".score-card");
  scoreCards.forEach((card) => {
    card.addEventListener("click", () => {
      const radio = card.querySelector('input[name="target_score"]');
      if (radio) {
        radio.checked = true;
      }
      scoreCards.forEach((c) => c.classList.remove("active"));
      card.classList.add("active");

      // Update button text to clearly show selected score
      if (state.currentDocId) {
        const val = parseFloat(radio.value);
        let goalText = "Khá / Giỏi (7.0 - 8.0đ)";
        if (val < 6.5) goalText = "Qua Môn (5.0 - 6.5đ)";
        if (val >= 8.5) goalText = "Xuất Sắc (8.5 - 10đ)";

        const actionText = state.currentPlanId ? "🔄 Cập Nhật Lộ Trình Mới" : "🚀 Tạo Lộ Trình Ôn Thi";
        btnGeneratePlan.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5"></i> <span>${actionText} (${goalText})</span>`;
        lucide.createIcons();
      }
    });
  });

  // Plan Form Submit
  planForm.addEventListener("submit", handleGeneratePlan);

  // Views Switch
  viewTodoBtn.addEventListener("click", () => switchView("todo"));
  viewCalendarBtn.addEventListener("click", () => switchView("calendar"));
  viewKanbanBtn.addEventListener("click", () => switchView("kanban"));

  // Reschedule Action
  btnReschedule.addEventListener("click", handleReschedule);

  // Switch/Change Plan
  btnChangePlan.addEventListener("click", () => {
    setupSection.classList.remove("hidden");
    setupSection.scrollIntoView({ behavior: "smooth" });
  });

  // Chat
  btnToggleChat.addEventListener("click", () => {
    chatWindow.classList.toggle("hidden");
    if (!chatWindow.classList.contains("hidden")) {
      chatInput.focus();
    }
  });
  btnCloseChat.addEventListener("click", () => chatWindow.classList.add("hidden"));
  chatForm.addEventListener("submit", handleSendMessage);

  // Quick Chat Prompts
  document.querySelectorAll(".quick-prompt").forEach((btn) => {
    btn.addEventListener("click", () => {
      chatInput.value = btn.textContent.trim().replace(/^[^\w\s]+/, "").trim();
      handleSendMessage(new Event("submit"));
    });
  });

  // Settings
  btnOpenSettings.addEventListener("click", () => settingsModal.classList.remove("hidden"));
  btnCloseSettings.addEventListener("click", () => settingsModal.classList.add("hidden"));
  btnSaveSettings.addEventListener("click", () => {
    state.geminiApiKey = settingsApiKey.value.trim();
    localStorage.setItem("examplan_gemini_key", state.geminiApiKey);
    settingsModal.classList.add("hidden");
    alert("Đã lưu cấu hình API Key!");
  });
}

// --- Staged Files Management (Review & Individual Delete) ---

function getAuthHeaders() {
  const headers = {};
  if (state.authToken) {
    headers["Authorization"] = `Bearer ${state.authToken}`;
  }
  return headers;
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function addStagedFiles(files) {
  const arr = Array.from(files);
  arr.forEach((f) => {
    if (!state.stagedFiles.some((item) => item.name === f.name && item.size === f.size)) {
      state.stagedFiles.push(f);
    }
  });
  renderSelectedFiles();
}

function renderSelectedFiles() {
  if (!state.stagedFiles || state.stagedFiles.length === 0) {
    selectedFilesContainer.classList.add("hidden");
    return;
  }

  selectedFilesContainer.classList.remove("hidden");
  stagedCount.textContent = state.stagedFiles.length;
  
  if (state.currentDocId) {
    btnAnalysisText.textContent = `Phân Tích Lại & Tạo Lộ Trình Mới (${state.stagedFiles.length} Tệp Đã Chọn)`;
  } else {
    btnAnalysisText.textContent = `Bắt Đầu Phân Tích (${state.stagedFiles.length} Tệp Đã Chọn)`;
  }

  selectedFilesList.innerHTML = state.stagedFiles
    .map((file, idx) => {
      const ext = (file.name.split(".").pop() || "FILE").toUpperCase();
      let badgeBg = "bg-indigo-100 text-indigo-700";
      if (ext === "PDF") badgeBg = "bg-rose-100 text-rose-700";
      if (ext === "DOCX" || ext === "DOC") badgeBg = "bg-blue-100 text-blue-700";
      if (ext === "TXT") badgeBg = "bg-emerald-100 text-emerald-700";

      return `
        <div class="flex items-center justify-between p-2 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-indigo-300 transition group" data-idx="${idx}">
          <div class="flex items-center gap-2.5 truncate">
            <span class="px-2 py-0.5 rounded text-[10px] font-extrabold ${badgeBg}">
              ${ext}
            </span>
            <div class="truncate">
              <p class="text-xs font-bold text-slate-800 truncate" title="${file.name}">${file.name}</p>
              <span class="text-[10px] text-slate-400">${formatBytes(file.size)}</span>
            </div>
          </div>
          <!-- Single File Delete Button -->
          <button type="button" class="btn-delete-single-staged p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition" data-idx="${idx}" title="Xóa tệp ${file.name}">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>
      `;
    })
    .join("");

  lucide.createIcons();

  // Attach individual delete event listener for each single file
  selectedFilesList.querySelectorAll(".btn-delete-single-staged").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.getAttribute("data-idx"), 10);
      const targetFile = state.stagedFiles[idx];
      if (!targetFile) return;

      // Remove the single selected file
      state.stagedFiles.splice(idx, 1);
      renderSelectedFiles();
      fileInput.value = "";

      // If already analyzed: update/re-analyze
      if (state.currentDocId) {
        if (state.stagedFiles.length === 0) {
          try {
            await fetch(`/api/documents/${state.currentDocId}`, { method: "DELETE" });
          } catch (_) {}
          state.currentDocId = null;
          state.currentPlanId = null;
          state.currentPlanData = null;
          docResultCard.classList.add("hidden");
          planDashboard.classList.add("hidden");
          btnGeneratePlan.disabled = true;
          btnGeneratePlan.className = "w-full py-3.5 px-4 rounded-xl text-white font-bold bg-slate-400 cursor-not-allowed transition-all flex items-center justify-center gap-2";
          btnGeneratePlan.innerHTML = `<i data-lucide="zap" class="w-5 h-5"></i> <span>Vui lòng tải đề cương trước</span>`;
          lucide.createIcons();
          return;
        }

        // If files are real File objects, re-analyze remaining files
        const allRealFiles = state.stagedFiles.every((f) => f instanceof File);
        if (allRealFiles) {
          await handleFileUpload(state.stagedFiles);
        } else {
          // If virtual / sample files, remove matching topic if code exists
          if (targetFile.topic_code) {
            try {
              await fetch(`/api/documents/${state.currentDocId}/topics/${targetFile.topic_code}`, { method: "DELETE" });
            } catch (_) {}
            state.currentDocTopics = state.currentDocTopics.filter((t) => t.code !== targetFile.topic_code);
            renderTopicsPreview(state.currentDocTopics);
          }
          btnGeneratePlan.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5"></i> <span>Tạo Lộ Trình Mới (${state.stagedFiles.length} Tệp Còn Lại)</span>`;
          lucide.createIcons();
        }
      }
    });
  });
}

// --- Upload & Analysis Handlers ---
async function handleFileUpload(files) {
  const fileList = files instanceof FileList || Array.isArray(files) ? Array.from(files) : [files];
  if (!fileList.length) return;
  state.uploadedFileObjects = Array.from(fileList);

  const formData = new FormData();
  if (state.geminiApiKey) {
    formData.append("gemini_api_key", state.geminiApiKey);
  }

  let endpoint = "/api/documents/upload";
  if (fileList.length > 1) {
    endpoint = "/api/documents/upload-multiple";
    fileList.forEach((f) => formData.append("files", f));
  } else {
    formData.append("file", fileList[0]);
  }

  showLoading(true);
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Không thể tải lên file.");
    }
    const data = await res.json();
    displayDocumentResult(data);
  } catch (err) {
    alert("Lỗi tải tệp: " + err.message);
  } finally {
    showLoading(false);
  }
}

async function handleUrlUpload() {
  const url = urlInput.value.trim();
  if (!url) {
    alert("Vui lòng nhập đường link!");
    return;
  }

  showLoading(true);
  try {
    const headers = { "Content-Type": "application/json", ...getAuthHeaders() };
    const res = await fetch("/api/documents/url", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        url: url,
        gemini_api_key: state.geminiApiKey || null
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Không thể cào dữ liệu từ link.");
    }
    const data = await res.json();
    displayDocumentResult(data);
  } catch (err) {
    alert("Lỗi cào URL: " + err.message);
  } finally {
    showLoading(false);
  }
}

async function handleLoadSample() {
  showLoading(true);
  try {
    const res = await fetch("/api/demo/load-sample", { method: "POST", headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Không thể tải dữ liệu mẫu.");
    const data = await res.json();
    displayDocumentResult(data);
  } catch (err) {
    alert("Lỗi: " + err.message);
  } finally {
    showLoading(false);
  }
}

function showLoading(isLoading) {
  if (isLoading) {
    analysisLoading.classList.remove("hidden");
    docResultCard.classList.add("hidden");
    btnGeneratePlan.disabled = true;
    btnGeneratePlan.className = "w-full py-3.5 px-4 rounded-xl text-white font-bold bg-slate-400 cursor-not-allowed transition-all flex items-center justify-center gap-2";
    btnGeneratePlan.innerHTML = `<span class="animate-spin mr-2">⏳</span> Đang phân tích đề cương...`;
  } else {
    analysisLoading.classList.add("hidden");
  }
}


// --- Authentication & User Persistence ---
async function initAuth() {
  // Fetch public backend config (Google Client ID)
  try {
    const cfgRes = await fetch("/api/config");
    if (cfgRes.ok) {
      const cfg = await cfgRes.json();
      state.googleClientId = cfg.google_client_id || "";
    }
  } catch (_) {}

  // Initialize Google Identity Services SDK
  initGoogleAuth();

  if (state.authToken) {
    try {
      const res = await fetch("/api/auth/me", { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        state.currentUser = data.user;
        state.authToken = data.token;
        localStorage.setItem("examplan_auth_token", data.token);
        updateAuthUI();
        return;
      }
    } catch (_) {}
  }

  // If no valid session, auto-initialize a Guest session
  await loginAsGuest(false);
}

function updateAuthUI() {
  if (!state.currentUser) {
    if (btnOpenLogin) btnOpenLogin.classList.remove("hidden");
    if (userProfileWidget) userProfileWidget.classList.add("hidden");
    updateStorageBadge(false);
    return;
  }

  const u = state.currentUser;
  if (btnOpenLogin) btnOpenLogin.classList.add("hidden");
  if (userProfileWidget) userProfileWidget.classList.remove("hidden");

  if (userAvatar) userAvatar.src = u.avatar_url || `https://api.dicebear.com/7.x/initials/svg?seed=${u.name}`;
  if (userDisplayName) userDisplayName.textContent = u.name || "Người dùng";
  if (userDropdownEmail) userDropdownEmail.textContent = u.email || "Khách (Chưa đăng ký)";

  if (userProviderBadge) {
    if (u.provider === "google") {
      userProviderBadge.className = "inline-block px-1.5 py-0.2 text-[9px] font-extrabold rounded bg-red-100 text-red-700 uppercase";
      userProviderBadge.textContent = "GMAIL";
    } else if (u.provider === "facebook") {
      userProviderBadge.className = "inline-block px-1.5 py-0.2 text-[9px] font-extrabold rounded bg-blue-100 text-blue-700 uppercase";
      userProviderBadge.textContent = "FACEBOOK";
    } else {
      userProviderBadge.className = "inline-block px-1.5 py-0.2 text-[9px] font-extrabold rounded bg-amber-100 text-amber-700 uppercase";
      userProviderBadge.textContent = "KHÁCH";
    }
  }

  updateStorageBadge(!u.is_guest);
  lucide.createIcons();
}

function updateStorageBadge(isPermanent) {
  if (!docStorageBadge) return;
  if (!state.currentDocId) {
    docStorageBadge.innerHTML = "";
    return;
  }

  if (isPermanent && state.currentUser && !state.currentUser.is_guest) {
    docStorageBadge.innerHTML = `
      <div class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-800 rounded-xl border border-emerald-200 text-xs font-semibold">
        <i data-lucide="shield-check" class="w-4 h-4 text-emerald-600"></i>
        <span>Đã lưu vĩnh viễn vào tài khoản (${escapeHtml(state.currentUser.name)})</span>
      </div>
    `;
  } else {
    docStorageBadge.innerHTML = `
      <div class="flex items-center justify-between gap-3 p-2.5 bg-amber-50 text-amber-900 rounded-xl border border-amber-200 text-xs font-medium w-full">
        <span class="flex items-center gap-1.5">
          <i data-lucide="alert-triangle" class="w-4 h-4 text-amber-600 shrink-0"></i>
          <span>Tài khoản Khách: Tài liệu này <strong>chưa được lưu vĩnh viễn</strong>.</span>
        </span>
        <button type="button" class="btn-prompt-login px-3 py-1 bg-amber-200/80 hover:bg-amber-300 text-amber-900 font-bold rounded-lg transition text-[11px] cursor-pointer shrink-0">
          Đăng nhập để lưu ngay
        </button>
      </div>
    `;

    docStorageBadge.querySelectorAll(".btn-prompt-login").forEach((b) => {
      b.addEventListener("click", () => {
        if (authModal) authModal.classList.remove("hidden");
      });
    });
  }
  lucide.createIcons();
}

async function loginAsGuest(showNotification = true) {
  try {
    const res = await fetch("/api/auth/guest", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      state.currentUser = data.user;
      state.authToken = data.token;
      localStorage.setItem("examplan_auth_token", data.token);
      updateAuthUI();
      if (showNotification) {
        if (authModal) authModal.classList.add("hidden");
        alert("👋 Bạn đang dùng thử với tư cách Khách. Bạn có thể đăng nhập bất cứ lúc nào để lưu vĩnh viễn đề cương!");
      }
    }
  } catch (e) {
    console.warn("Guest auth error:", e);
  }
}


// --- Google Identity Services (OAuth 2.0) Integration ---
function initGoogleAuth() {
  if (typeof google === "undefined" || !google.accounts || !google.accounts.id) {
    setTimeout(initGoogleAuth, 300);
    return;
  }

  const gContainer = document.getElementById("google-button-official");
  const fallbackBtn = document.getElementById("btn-login-google");

  if (!state.googleClientId) {
    if (gContainer) {
      gContainer.innerHTML = `
        <div class="w-full p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-center text-xs text-amber-800 space-y-1">
          <p class="font-bold flex items-center justify-center gap-1.5">
            <i data-lucide="info" class="w-4 h-4 text-amber-600"></i> Chưa điền GOOGLE_CLIENT_ID
          </p>
          <p class="text-[11px] text-slate-600 leading-snug">
            Khai báo <code>GOOGLE_CLIENT_ID</code> trong file <code>.env</code> để hiển thị nút Google chính chủ.
          </p>
          <button type="button" id="btn-quick-config-google" class="mt-1 px-2.5 py-1 bg-amber-200/70 hover:bg-amber-300 text-amber-900 font-bold rounded-lg text-[10px] transition cursor-pointer">
            ⚙️ Nhập Client ID để thử ngay
          </button>
        </div>
      `;
      lucide.createIcons();

      const btnQuick = document.getElementById("btn-quick-config-google");
      if (btnQuick) {
        btnQuick.addEventListener("click", (e) => {
          e.stopPropagation();
          const cid = prompt("Dán Google OAuth Client ID của bạn vào đây:");
          if (cid && cid.trim()) {
            state.googleClientId = cid.trim();
            initGoogleAuth();
          }
        });
      }
    }
    if (fallbackBtn) fallbackBtn.classList.remove("hidden");
    return;
  }

  try {
    google.accounts.id.initialize({
      client_id: state.googleClientId,
      callback: handleGoogleCredentialResponse,
      auto_select: false,
      cancel_on_tap_outside: true
    });

    if (gContainer) {
      gContainer.innerHTML = "";
      google.accounts.id.renderButton(gContainer, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        logo_alignment: "left",
        width: 380
      });
    }

    if (fallbackBtn) fallbackBtn.classList.add("hidden");
  } catch (err) {
    console.warn("[GIS] Error initializing Google Auth:", err);
    if (fallbackBtn) fallbackBtn.classList.remove("hidden");
  }
}

async function handleGoogleCredentialResponse(response) {
  if (!response || !response.credential) {
    alert("Không nhận được mã xác thực từ Google. Vui lòng thử lại.");
    return;
  }

  const guestToken = state.currentUser && state.currentUser.is_guest ? state.authToken : null;

  try {
    const res = await fetch("/api/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        credential: response.credential,
        guest_token: guestToken
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Không thể xác thực với Google.");
    }

    const data = await res.json();
    state.currentUser = data.user;
    state.authToken = data.token;
    localStorage.setItem("examplan_auth_token", data.token);

    if (authModal) authModal.classList.add("hidden");
    updateAuthUI();
    alert(`🎉 Đăng nhập Google thành công với tài khoản: ${data.user.email}!\nTất cả tài liệu của bạn đã được LƯU VĨNH VIỄN.`);
  } catch (err) {
    alert("Lỗi đăng nhập Google: " + err.message);
  }
}

async function handleGoogleLogin() {
  if (!state.googleClientId) {
    const cid = prompt("Chưa cấu hình GOOGLE_CLIENT_ID trong file .env!\n\nBạn có thể dán nhanh Google Client ID vào đây để dùng thử ngay:\n(Hoặc mở file .env và điền GOOGLE_CLIENT_ID)");
    if (cid && cid.trim()) {
      state.googleClientId = cid.trim();
      initGoogleAuth();
    }
    return;
  }

  if (typeof google !== "undefined" && google.accounts && google.accounts.id) {
    google.accounts.id.prompt((notification) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        const btn = document.querySelector("#google-button-official div[role=button]");
        if (btn) btn.click();
      }
    });
  } else {
    alert("Đang tải thư viện Google Identity Services, vui lòng thử lại sau 2 giây.");
  }
}


async function handleFacebookLogin() {
  const defaultName = "Sinh Viên Facebook";
  const nameInput = prompt("Nhập tên hiển thị tài khoản Facebook của bạn:", defaultName);
  if (!nameInput || !nameInput.trim()) return;

  const name = nameInput.trim();
  const guestToken = state.currentUser && state.currentUser.is_guest ? state.authToken : null;

  try {
    const res = await fetch("/api/auth/facebook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        email: `${name.toLowerCase().replace(/\s+/g, "")}@facebook.com`,
        facebook_id: "fb_" + Date.now(),
        guest_token: guestToken
      })
    });

    if (!res.ok) throw new Error("Không thể kết nối tài khoản Facebook.");
    const data = await res.json();
    state.currentUser = data.user;
    state.authToken = data.token;
    localStorage.setItem("examplan_auth_token", data.token);

    if (authModal) authModal.classList.add("hidden");
    updateAuthUI();
    alert(`🎉 Đăng nhập Facebook thành công với tên: ${name}!\nTất cả tài liệu của bạn đã được LƯU VĨNH VIỄN.`);
  } catch (err) {
    alert("Lỗi đăng nhập: " + err.message);
  }
}

function handleLogout() {
  if (!confirm("Bạn có chắc chắn muốn đăng xuất không?")) return;
  localStorage.removeItem("examplan_auth_token");
  state.authToken = "";
  state.currentUser = null;
  if (userDropdownMenu) userDropdownMenu.classList.add("hidden");
  loginAsGuest(false);
  alert("👋 Đã đăng xuất thành công. Đang chuyển về chế độ Khách.");
}

async function openLibraryModal() {
  if (userDropdownMenu) userDropdownMenu.classList.add("hidden");
  if (!state.currentUser || state.currentUser.is_guest) {
    alert("Bạn đang ở chế độ Khách nên chưa có thư viện lưu vĩnh viễn. Hãy đăng nhập Gmail hoặc Facebook để lưu tài liệu!");
    if (authModal) authModal.classList.remove("hidden");
    return;
  }

  if (libraryModal) libraryModal.classList.remove("hidden");
  if (libraryItemsList) libraryItemsList.innerHTML = `<div class="py-8 text-center text-xs text-slate-400"><span class="animate-spin inline-block mr-1">⏳</span> Đang tải thư viện tài liệu đã lưu...</div>`;

  try {
    const res = await fetch("/api/user/library", { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Không thể tải thư viện.");
    const data = await res.json();

    if (!data.documents || data.documents.length === 0) {
      libraryItemsList.innerHTML = `
        <div class="py-12 text-center space-y-2">
          <i data-lucide="folder-open" class="w-10 h-10 text-slate-300 mx-auto"></i>
          <p class="text-xs font-bold text-slate-600">Bạn chưa có tài liệu nào được lưu</p>
          <p class="text-[11px] text-slate-400">Hãy tải lên đề cương ôn thi để hệ thống tự động lưu vĩnh viễn vào tài khoản của bạn.</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    libraryItemsList.innerHTML = data.documents.map((d) => `
      <div class="p-3 bg-white rounded-2xl border border-slate-200 hover:border-indigo-300 transition shadow-sm flex items-center justify-between">
        <div class="flex items-center gap-3 truncate">
          <div class="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
            <i data-lucide="file-text" class="w-4 h-4"></i>
          </div>
          <div class="truncate">
            <p class="text-xs font-bold text-slate-800 truncate">${escapeHtml(d.subject_name || d.filename)}</p>
            <div class="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
              <span>${d.created_at}</span>
              <span>•</span>
              <span class="text-indigo-600 font-semibold">${d.topic_count} chủ đề</span>
              <span>•</span>
              <span class="text-emerald-600 font-semibold">Đã lưu vĩnh viễn</span>
            </div>
          </div>
        </div>
        <button type="button" class="btn-load-library-doc px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-sm shrink-0 cursor-pointer" data-id="${d.id}">
          Mở Lại
        </button>
      </div>
    `).join("");

    lucide.createIcons();

    libraryItemsList.querySelectorAll(".btn-load-library-doc").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const docId = btn.getAttribute("data-id");
        if (libraryModal) libraryModal.classList.add("hidden");
        showLoading(true);
        try {
          const res = await fetch(`/api/documents`);
          const allDocs = await res.json();
          const target = allDocs.find((x) => x.id == docId);
          if (target) {
            // Load this document
            state.currentDocId = target.id;
            docSubjectTitle.textContent = target.subject_name;
            docSummary.textContent = `Tài liệu đã lưu từ ${target.created_at}.`;
            docResultCard.classList.remove("hidden");
            setupSection.classList.remove("hidden");
            setupSection.scrollIntoView({ behavior: "smooth" });
            updateStorageBadge(true);
            updateStorageBadge(state.currentUser ? !state.currentUser.is_guest : false);
  btnGeneratePlan.disabled = false;
            btnGeneratePlan.className = "w-full py-3.5 px-4 rounded-xl text-white font-bold bg-indigo-600 hover:bg-indigo-700 shadow-lg hover:shadow-indigo-200 transition-all flex items-center justify-center gap-2 cursor-pointer";
            btnGeneratePlan.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5"></i> <span>Tạo Lộ Trình Ôn Thi (${target.subject_name})</span>`;
            lucide.createIcons();
          }
        } catch (e) {
          alert("Lỗi khi mở lại tài liệu: " + e.message);
        } finally {
          showLoading(false);
        }
      });
    });

  } catch (err) {
    libraryItemsList.innerHTML = `<div class="text-center py-6 text-xs text-rose-600">Lỗi: ${escapeHtml(err.message)}</div>`;
  }
}

function displayDocumentResult(data) {
  state.currentDocId = data.document_id;
  state.currentDocTopics = data.topics || [];

  docSubjectTitle.textContent = data.subject_name;
  docSummary.textContent = data.summary;

  // Render topics preview
  renderTopicsPreview(state.currentDocTopics);

  // If stagedFiles was empty (e.g. sample syllabus loaded), populate from data.files_list
  if (!state.stagedFiles || state.stagedFiles.length === 0) {
    if (data.files_list && data.files_list.length > 0) {
      state.stagedFiles = data.files_list.map((f, i) => ({
        name: f.name,
        size: 1024 * 1024 * (i + 1),
        topic_code: f.topic_code || `CH${i + 1}`
      }));
    }
  }

  // KEEP selected files container VISIBLE so user can remove finished files!
  renderSelectedFiles();
  docResultCard.classList.remove("hidden");

  // Enable Generate Button
  updateStorageBadge(state.currentUser ? !state.currentUser.is_guest : false);
  btnGeneratePlan.disabled = false;
  btnGeneratePlan.className = "w-full py-3.5 px-4 rounded-xl text-white font-bold bg-indigo-600 hover:bg-indigo-700 shadow-lg hover:shadow-indigo-200 transition-all flex items-center justify-center gap-2 cursor-pointer";
  btnGeneratePlan.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5"></i> <span>Tạo Lộ Trình Ôn Thi (${data.subject_name})</span>`;
  lucide.createIcons();
}

function renderTopicsPreview(topics) {
  if (!topicsPreviewList) return;
  topicsPreviewList.innerHTML = topics
    .map((t) => {
      let diffClass = "badge-diff-trung-binh";
      if (t.difficulty === "Dễ") diffClass = "badge-diff-de";
      if (t.difficulty === "Khó") diffClass = "badge-diff-kho";

      return `
      <div class="p-2.5 rounded-lg border border-slate-100 bg-slate-50 flex items-center justify-between text-xs">
        <div class="flex items-center gap-2 truncate">
          <span class="font-bold text-slate-800">${t.title}</span>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${diffClass}">${t.difficulty}</span>
          <span class="text-slate-400 text-[11px]">${t.estimated_hours}h</span>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderActiveFiles() {
  if (!activeFilesContainer || !activeFilesList) return;

  if (!state.activeFiles || state.activeFiles.length === 0) {
    activeFilesContainer.classList.add("hidden");
    return;
  }

  activeFilesContainer.classList.remove("hidden");
  if (activeFilesCount) activeFilesCount.textContent = state.activeFiles.length;

  activeFilesList.innerHTML = state.activeFiles
    .map((file, idx) => {
      const ext = (file.name.split(".").pop() || "FILE").toUpperCase();
      let badgeBg = "bg-indigo-100 text-indigo-700";
      if (ext === "PDF") badgeBg = "bg-rose-100 text-rose-700";
      if (ext === "DOCX" || ext === "DOC") badgeBg = "bg-blue-100 text-blue-700";
      if (ext === "TXT") badgeBg = "bg-emerald-100 text-emerald-700";

      return `
        <div class="flex items-center justify-between p-2 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-indigo-300 transition group" data-file-idx="${idx}">
          <div class="flex items-center gap-2.5 truncate">
            <span class="px-2 py-0.5 rounded text-[10px] font-extrabold ${badgeBg}">
              ${ext}
            </span>
            <div class="truncate">
              <p class="text-xs font-semibold text-slate-800 truncate" title="${file.name}">${file.name}</p>
              <span class="text-[10px] text-emerald-600 flex items-center gap-1 font-medium">
                <i data-lucide="check-circle" class="w-3 h-3"></i> Đang trong lộ trình ôn tập
              </span>
            </div>
          </div>
          <!-- Individual Trash Button for deleting completed/unneeded document -->
          <button type="button" class="btn-delete-active-file p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition" data-file-idx="${idx}" title="Xóa tài liệu này (đã học xong)">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>
      `;
    })
    .join("");

  lucide.createIcons();

  // Attach individual delete event listener for each active file
  activeFilesList.querySelectorAll(".btn-delete-active-file").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.getAttribute("data-file-idx"), 10);
      const targetFile = state.activeFiles[idx];
      if (!targetFile) return;

      // If only 1 file remains, confirm deleting the entire document
      if (state.activeFiles.length <= 1) {
        if (!confirm(`Tệp "${targetFile.name}" là tài liệu duy nhất còn lại. Bạn có chắc muốn xóa môn học này để tải tài liệu mới không?`)) {
          return;
        }
        try {
          if (state.currentDocId) {
            await fetch(`/api/documents/${state.currentDocId}`, { method: "DELETE" });
          }
          state.currentDocId = null;
          state.currentPlanId = null;
          state.currentPlanData = null;
          state.activeFiles = [];
          state.uploadedFileObjects = [];
          state.currentDocTopics = [];
          docResultCard.classList.add("hidden");
          planDashboard.classList.add("hidden");
          btnGeneratePlan.disabled = true;
          btnGeneratePlan.className = "w-full py-3.5 px-4 rounded-xl text-white font-bold bg-slate-400 cursor-not-allowed transition-all flex items-center justify-center gap-2";
          btnGeneratePlan.innerHTML = `<i data-lucide="zap" class="w-5 h-5"></i> <span>Vui lòng tải đề cương trước</span>`;
          lucide.createIcons();
          alert("🗑️ Đã xóa toàn bộ tài liệu!");
        } catch (err) {
          alert("Lỗi khi xóa tài liệu: " + err.message);
        }
        return;
      }

      // Multiple files case: confirm deleting this one completed file
      if (!confirm(`Bạn có chắc muốn xóa tệp "${targetFile.name}" (đã học xong hoặc bỏ qua) và tạo lại lộ trình mới không?`)) {
        return;
      }

      // If user uploaded real files, remove from list and re-analyze
      if (state.uploadedFileObjects && state.uploadedFileObjects.length > 1) {
        const fIdx = state.uploadedFileObjects.findIndex((f) => f.name === targetFile.name);
        if (fIdx !== -1) {
          state.uploadedFileObjects.splice(fIdx, 1);
        }
        await handleFileUpload(state.uploadedFileObjects);
        return;
      }

      // Sample / Preloaded mode: remove from state & delete topic in backend
      if (targetFile.topic_code && state.currentDocId) {
        try {
          await fetch(`/api/documents/${state.currentDocId}/topics/${targetFile.topic_code}`, {
            method: "DELETE"
          });
        } catch (err) {
          console.warn("Could not delete topic via API:", err);
        }
      }

      // Remove from active files list
      state.activeFiles.splice(idx, 1);
      if (targetFile.topic_code) {
        state.currentDocTopics = state.currentDocTopics.filter((t) => t.code !== targetFile.topic_code);
      } else {
        state.currentDocTopics.splice(idx, 1);
      }

      renderActiveFiles();
      renderTopicsPreview(state.currentDocTopics);

      // Update button text to invite generating updated plan
      updateStorageBadge(state.currentUser ? !state.currentUser.is_guest : false);
  btnGeneratePlan.disabled = false;
      btnGeneratePlan.className = "w-full py-3.5 px-4 rounded-xl text-white font-bold bg-indigo-600 hover:bg-indigo-700 shadow-lg hover:shadow-indigo-200 transition-all flex items-center justify-center gap-2 cursor-pointer";
      btnGeneratePlan.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5"></i> <span>Tạo Lộ Trình Mới (${state.activeFiles.length} Tệp Còn Lại)</span>`;
      lucide.createIcons();
    });
  });
}

// --- Study Plan Generation ---
async function handleGeneratePlan(e) {
  e.preventDefault();
  if (!state.currentDocId) {
    alert("Vui lòng tải lên tài liệu đề cương trước!");
    return;
  }

  const targetScore = parseFloat(document.querySelector('input[name="target_score"]:checked').value);
  const examDate = examDateInput.value;
  const dailyHours = parseFloat(dailyHoursSlider.value);

  let weeklySchedulePayload = null;
  if (state.timetableMode === "weekly") {
    weeklySchedulePayload = {
      mon: parseFloat(document.getElementById("wh-mon").value) || 0.0,
      tue: parseFloat(document.getElementById("wh-tue").value) || 0.0,
      wed: parseFloat(document.getElementById("wh-wed").value) || 0.0,
      thu: parseFloat(document.getElementById("wh-thu").value) || 0.0,
      fri: parseFloat(document.getElementById("wh-fri").value) || 0.0,
      sat: parseFloat(document.getElementById("wh-sat").value) || 0.0,
      sun: parseFloat(document.getElementById("wh-sun").value) || 0.0,
    };
  }

  btnGeneratePlan.disabled = true;
  btnGeneratePlan.innerHTML = `<span class="animate-spin mr-2">⚙️</span> Thuật toán đang xếp lịch Spaced Repetition...`;

  try {
    const headers = { "Content-Type": "application/json", ...getAuthHeaders() };
    const res = await fetch("/api/plans/generate", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        document_id: state.currentDocId,
        exam_date: examDate,
        daily_hours: dailyHours,
        target_score: targetScore,
        weekly_schedule: weeklySchedulePayload,
        gemini_api_key: state.geminiApiKey || null,
        active_topic_codes: state.currentDocTopics.length > 0 ? state.currentDocTopics.map((t) => t.code) : null
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Không thể tạo kế hoạch.");
    }

    const planData = await res.json();
    renderPlanDashboard(planData);
  } catch (err) {
    alert("Lỗi lập lộ trình: " + err.message);
  } finally {
    updateStorageBadge(state.currentUser ? !state.currentUser.is_guest : false);
  btnGeneratePlan.disabled = false;
    btnGeneratePlan.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5"></i> <span>Tạo Lộ Trình Ôn Thi</span>`;
    lucide.createIcons();
  }
}

function renderPlanDashboard(plan) {
  state.currentPlanId = plan.id;
  state.currentPlanData = plan;

  dashSubjectBadge.textContent = plan.subject_name;
  dashTargetBadge.textContent = `Mục tiêu: ${plan.target_score} Điểm`;
  dashPlanTitle.textContent = plan.title;
  dashDaysLeft.textContent = plan.days_left;
  dashTasksDone.textContent = plan.completed_tasks;
  dashTasksTotal.textContent = plan.total_tasks;
  dashProgressPct.textContent = `${plan.progress_percent}%`;
  dashProgressBar.style.width = `${plan.progress_percent}%`;

  btnExportIcal.href = `/api/plans/${plan.id}/export-ical`;

  renderDailyTodoList(plan.tasks);
  renderCalendarView(plan.tasks);
  renderKanbanView(plan.tasks);

  planDashboard.classList.remove("hidden");
  planDashboard.scrollIntoView({ behavior: "smooth" });
  lucide.createIcons();
}

// --- Render Views ---
function renderDailyTodoList(tasks) {
  // Group tasks by study_date
  const grouped = {};
  tasks.forEach((t) => {
    if (!grouped[t.study_date]) {
      grouped[t.study_date] = [];
    }
    grouped[t.study_date].push(t);
  });

  const dates = Object.keys(grouped).sort();
  const todayStr = new Date().toISOString().split("T")[0];

  viewTodoContent.innerHTML = dates
    .map((dateStr) => {
      const dayTasks = grouped[dateStr];
      const dayNum = dayTasks[0].day_number;
      const isToday = dateStr === todayStr;
      const isPast = dateStr < todayStr;
      const allCompleted = dayTasks.every((t) => t.is_completed);

      // Date header formatting
      const dateObj = new Date(dateStr);
      const formattedDate = dateObj.toLocaleDateString("vi-VN", {
        weekday: "short",
        day: "2-digit",
        month: "2-digit"
      });

      return `
      <div class="glass-card rounded-2xl p-5 border ${isToday ? "border-indigo-500 ring-2 ring-indigo-100" : "border-slate-200"} bg-white transition">
        <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <span class="w-8 h-8 rounded-xl ${allCompleted ? "bg-emerald-100 text-emerald-700" : (isToday ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-700")} flex items-center justify-center text-xs font-bold">
              ${allCompleted ? "✓" : `N${dayNum}`}
            </span>
            <div>
              <h3 class="text-sm font-bold text-slate-900 flex items-center gap-2">
                Ngày ${dayNum}: ${formattedDate}
                ${isToday ? '<span class="px-2 py-0.5 rounded-full text-[10px] bg-indigo-100 text-indigo-700 font-extrabold">Hôm nay</span>' : ""}
                ${isPast && !allCompleted ? '<span class="px-2 py-0.5 rounded-full text-[10px] bg-amber-100 text-amber-800 font-extrabold">Bị trễ</span>' : ""}
              </h3>
                            <span class="text-xs text-indigo-700 font-semibold bg-indigo-50 px-2 py-0.5 rounded-md">
                ${dayTasks.length} nhiệm vụ: ${dayTasks.reduce((acc, x) => acc + x.estimated_minutes, 0)} phút
              </span>
            </div>
          </div>
          <div class="text-xs font-semibold text-slate-500">
            ${dayTasks.filter((t) => t.is_completed).length}/${dayTasks.length} hoàn thành
          </div>
        </div>

        <div class="space-y-2.5">
          ${dayTasks.map((task) => renderTaskItem(task)).join("")}
        </div>
      </div>
    `;
    })
    .join("");

  lucide.createIcons();
}

function renderTaskItem(task) {
  let typeBadge = "bg-indigo-50 text-indigo-700 border-indigo-200";
  let typeLabel = "Học Mới";

  if (task.task_type === "spaced_review") {
    typeBadge = "bg-purple-50 text-purple-700 border-purple-200";
    typeLabel = "Ôn Lặp Lại";
  } else if (task.task_type === "practice_exam") {
    typeBadge = "bg-amber-50 text-amber-700 border-amber-200";
    typeLabel = "Thi Thử Mock";
  } else if (task.task_type === "final_review") {
    typeBadge = "bg-rose-50 text-rose-700 border-rose-200";
    typeLabel = "Tổng Ôn";
  }

  let diffClass = "badge-diff-trung-binh";
  if (task.difficulty === "Dễ") diffClass = "badge-diff-de";
  if (task.difficulty === "Khó") diffClass = "badge-diff-kho";

  return `
    <div class="flex items-start gap-3 p-3 rounded-xl border border-slate-100 hover:border-indigo-300 hover:bg-slate-50/70 transition group cursor-pointer" onclick="handleTaskItemClick(event, ${task.id})">
      <div class="pt-0.5" onclick="event.stopPropagation()">
        <input type="checkbox" id="task-${task.id}" class="task-checkbox w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer" ${task.is_completed ? "checked" : ""} onchange="handleToggleTask(${task.id})">
      </div>
      <div class="flex-1 select-none">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-1">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${typeBadge}">${typeLabel}</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${diffClass}">${task.difficulty}</span>
            <span class="text-slate-400 text-[11px] font-medium flex items-center gap-1">
              <i data-lucide="clock" class="w-3 h-3"></i> ${task.estimated_minutes}p
            </span>
          </div>
          <span class="opacity-0 group-hover:opacity-100 transition-opacity text-[11px] font-bold text-indigo-600 flex items-center gap-1">
            <i data-lucide="sparkles" class="w-3 h-3"></i> Xem chi tiết & Quiz
          </span>
        </div>
        <h4 class="task-title text-xs font-bold text-slate-800 ${task.is_completed ? "line-through text-slate-400" : "group-hover:text-indigo-600"} transition-colors">${task.title}</h4>
        ${task.description ? `<p class="text-[11px] text-slate-500 mt-0.5 leading-relaxed line-clamp-2">${task.description}</p>` : ""}
      </div>
    </div>
  `;
}

function renderCalendarView(tasks) {
  const grouped = {};
  tasks.forEach((t) => {
    if (!grouped[t.study_date]) grouped[t.study_date] = [];
    grouped[t.study_date].push(t);
  });

  const dates = Object.keys(grouped).sort();
  if (!dates.length) return;

  const todayStr = new Date().toISOString().split("T")[0];

  calendarGrid.innerHTML = dates
    .map((dateStr) => {
      const dayTasks = grouped[dateStr];
      const isToday = dateStr === todayStr;
      const allCompleted = dayTasks.every((t) => t.is_completed);

      const d = new Date(dateStr);
      const dayDisplay = `${d.getDate()}/${d.getMonth() + 1}`;

      return `
      <div class="p-3 min-h-28 rounded-xl border ${isToday ? "border-indigo-600 bg-indigo-50/30 ring-2 ring-indigo-200" : "border-slate-200 bg-white"} flex flex-col justify-between text-left">
        <div>
          <div class="flex items-center justify-between text-xs font-bold mb-1.5">
            <span class="${isToday ? "text-indigo-600 font-extrabold" : "text-slate-700"}">${dayDisplay}</span>
            <span class="text-[10px] px-1.5 py-0.2 rounded-full ${allCompleted ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}">
              ${dayTasks.filter((x) => x.is_completed).length}/${dayTasks.length}
            </span>
          </div>
          <div class="space-y-1">
            ${dayTasks.slice(0, 2).map((t) => `
              <div onclick="openStudyModal(${t.id})" class="text-[10px] truncate p-1 rounded cursor-pointer hover:border-indigo-300 hover:text-indigo-700 transition ${t.is_completed ? "line-through text-slate-400 bg-slate-100" : "text-slate-700 bg-slate-50 border border-slate-100"}" title="${t.title} - Bấm để học chi tiết">
                ${t.title}
              </div>
            `).join("")}
            ${dayTasks.length > 2 ? `<div class="text-[9px] text-slate-400 pl-1">+${dayTasks.length - 2} nhiệm vụ khác</div>` : ""}
          </div>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderKanbanView(tasks) {
  const todos = tasks.filter((t) => !t.is_completed && t.task_type !== "spaced_review");
  const reviews = tasks.filter((t) => !t.is_completed && t.task_type === "spaced_review");
  const dones = tasks.filter((t) => t.is_completed);

  kanbanTodoCount.textContent = todos.length;
  kanbanReviewCount.textContent = reviews.length;
  kanbanDoneCount.textContent = dones.length;

  kanbanTodoList.innerHTML = todos.map((t) => renderKanbanCard(t)).join("");
  kanbanReviewList.innerHTML = reviews.map((t) => renderKanbanCard(t)).join("");
  kanbanDoneList.innerHTML = dones.map((t) => renderKanbanCard(t)).join("");

  lucide.createIcons();
}

function renderKanbanCard(t) {
  return `
    <div class="p-3 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow hover:border-indigo-300 transition cursor-pointer" onclick="handleTaskItemClick(event, ${t.id})">
      <div class="flex items-center justify-between text-[10px] font-bold text-slate-500 mb-1">
        <span>Ngày ${t.day_number} (${t.study_date})</span>
        <span class="text-indigo-600">${t.estimated_minutes}p</span>
      </div>
      <h5 class="text-xs font-bold text-slate-800 hover:text-indigo-600 transition-colors ${t.is_completed ? "line-through text-slate-400" : ""}">${t.title}</h5>
      <div class="mt-2.5 flex items-center justify-between pt-2 border-t border-slate-100" onclick="event.stopPropagation()">
        <span class="text-[10px] px-2 py-0.5 rounded-full ${t.difficulty === "Khó" ? "badge-diff-kho" : "badge-diff-de"}">${t.difficulty}</span>
        <button onclick="handleToggleTask(${t.id})" class="text-[11px] font-bold ${t.is_completed ? "text-slate-400" : "text-emerald-600 hover:text-emerald-700"} cursor-pointer">
          ${t.is_completed ? "Đã xong" : "Tick hoàn thành"}
        </button>
      </div>
    </div>
  `;
}

function switchView(viewName) {
  state.activeView = viewName;

  viewTodoBtn.className = "px-4 py-2 rounded-lg hover:text-slate-900 flex items-center gap-1.5";
  viewCalendarBtn.className = "px-4 py-2 rounded-lg hover:text-slate-900 flex items-center gap-1.5";
  viewKanbanBtn.className = "px-4 py-2 rounded-lg hover:text-slate-900 flex items-center gap-1.5";

  viewTodoContent.classList.add("hidden");
  viewCalendarContent.classList.add("hidden");
  viewKanbanContent.classList.add("hidden");

  if (viewName === "todo") {
    viewTodoBtn.className = "px-4 py-2 rounded-lg bg-white text-indigo-600 shadow-sm flex items-center gap-1.5";
    viewTodoContent.classList.remove("hidden");
  } else if (viewName === "calendar") {
    viewCalendarBtn.className = "px-4 py-2 rounded-lg bg-white text-indigo-600 shadow-sm flex items-center gap-1.5";
    viewCalendarContent.classList.remove("hidden");
  } else if (viewName === "kanban") {
    viewKanbanBtn.className = "px-4 py-2 rounded-lg bg-white text-indigo-600 shadow-sm flex items-center gap-1.5";
    viewKanbanContent.classList.remove("hidden");
  }
  lucide.createIcons();
}

// --- Toggle Task Checkbox ---
window.handleTaskItemClick = function(event, taskId) {
  // Prevent opening modal when checking checkbox directly
  if (event.target && (event.target.tagName === "INPUT" || event.target.closest("input"))) {
    return;
  }
  openStudyModal(taskId);
};

window.setTargetGoal = function(goal) {
  state.targetGoal = goal;
  if (goal === "basic") {
    goalFilterBasic.className = "px-2.5 py-1 rounded-md text-[11px] font-bold transition bg-indigo-600 text-white shadow-xs cursor-pointer";
    goalFilterAdvanced.className = "px-2.5 py-1 rounded-md text-[11px] font-semibold transition text-slate-600 hover:text-slate-900 cursor-pointer flex items-center gap-1";
  } else {
    goalFilterAdvanced.className = "px-2.5 py-1 rounded-md text-[11px] font-bold transition bg-indigo-600 text-white shadow-xs cursor-pointer flex items-center gap-1";
    goalFilterBasic.className = "px-2.5 py-1 rounded-md text-[11px] font-semibold transition text-slate-600 hover:text-slate-900 cursor-pointer";
  }

  // If Study Modal is currently open, refresh the lesson view for the new goal
  if (studyModal && !studyModal.classList.contains("hidden") && state.activeStudyTask) {
    openStudyModal(state.activeStudyTask.id, true);
  }
};

window.openStudyModal = async function(taskId, forceRefresh = false) {
  if (!studyModal) return;

  // Find task data from state (support both int and string comparisons)
  const task = state.currentPlanData?.tasks?.find((t) => String(t.id) === String(taskId));
  if (!task) return;

  state.activeStudyTask = task;
  studyModal.classList.remove("hidden");

  // Always reset to Tab 1 (Lesson & Quiz) when opening
  switchStudyModalTab("lesson");

  // Clear previous Q&A thread for this fresh modal session
  if (studyQaMessages) studyQaMessages.innerHTML = "";
  if (studyQaInput) studyQaInput.value = "";

  // Populate Task Header
  studyModalTitle.textContent = task.title;
  studyModalTopic.textContent = task.topic_title ? `Chủ đề: ${task.topic_title}` : `Ngày ${task.day_number} (${task.study_date})`;
  studyModalTime.innerHTML = `<i data-lucide="clock" class="w-3 h-3"></i> ${task.estimated_minutes} phút`;

  // Badges
  let typeLabel = "HỌC MỚI";
  let typeClass = "bg-indigo-50 text-indigo-700 border-indigo-200";
  if (task.task_type === "spaced_review") {
    typeLabel = "ÔN LẶP LẠI";
    typeClass = "bg-purple-50 text-purple-700 border-purple-200";
  } else if (task.task_type === "practice_exam") {
    typeLabel = "THI THỬ MOCK";
    typeClass = "bg-amber-50 text-amber-700 border-amber-200";
  } else if (task.task_type === "final_review") {
    typeLabel = "TỔNG ÔN";
    typeClass = "bg-rose-50 text-rose-700 border-rose-200";
  }
  studyModalBadgeType.textContent = typeLabel;
  studyModalBadgeType.className = `px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${typeClass}`;

  let diffClass = "badge-diff-trung-binh";
  if (task.difficulty === "Dễ") diffClass = "badge-diff-de";
  if (task.difficulty === "Khó") diffClass = "badge-diff-kho";
  studyModalBadgeDiff.textContent = task.difficulty;
  studyModalBadgeDiff.className = `px-2 py-0.5 rounded-full text-[10px] font-bold ${diffClass}`;

  updateStudyModalDoneButton(task.is_completed);

  // Render slides immediately from task data
  renderTaskSlides(task.image_urls || []);

  // Check in-memory cache for this task + targetGoal
  const cacheKey = `${taskId}_${state.targetGoal}`;
  if (!forceRefresh && state.studyLessonCache[cacheKey]) {
    studyModalLoading.classList.add("hidden");
    studyModalBody.classList.remove("hidden");
    renderStudyLessonContent(state.studyLessonCache[cacheKey]);
    lucide.createIcons();
    return;
  }

  // Show Loading & Fetch from RAG Endpoint
  studyModalLoading.classList.remove("hidden");
  studyModalBody.classList.add("hidden");
  lucide.createIcons();

  try {
    const res = await fetch(`/api/tasks/${taskId}/study-lesson`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({
        target_goal: state.targetGoal || "advanced",
        gemini_api_key: state.geminiApiKey || null
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Không thể tải kiến thức bài học.");
    }

    const data = await res.json();
    state.studyLessonCache[cacheKey] = data.lesson;

    if (data.task && data.task.image_urls) {
      task.image_urls = data.task.image_urls;
      renderTaskSlides(data.task.image_urls);
    }

    studyModalLoading.classList.add("hidden");
    studyModalBody.classList.remove("hidden");
    renderStudyLessonContent(data.lesson);
  } catch (err) {
    studyModalLoading.innerHTML = `
      <div class="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-700 text-xs">
        <p class="font-bold">Lỗi tải kiến thức bài học: ${err.message}</p>
        <button onclick="openStudyModal(${taskId}, true)" class="mt-2 px-3 py-1 bg-rose-600 text-white rounded-lg font-bold">Thử lại</button>
      </div>
    `;
  }
  lucide.createIcons();
};

function updateStudyModalDoneButton(isCompleted) {
  if (!btnStudyModalToggleDone) return;
  if (isCompleted) {
    btnStudyModalToggleDone.className = "px-4 py-2.5 rounded-xl font-bold text-xs bg-emerald-100 hover:bg-emerald-200 text-emerald-800 transition flex items-center gap-2 cursor-pointer border border-emerald-300";
    btnStudyModalToggleDone.innerHTML = `<i data-lucide="check-check" class="w-4 h-4 text-emerald-600"></i> <span>✓ Đã Hoàn Thành (Bấm để hủy)</span>`;
  } else {
    btnStudyModalToggleDone.className = "px-4 py-2.5 rounded-xl font-bold text-xs bg-indigo-600 hover:bg-indigo-700 text-white transition flex items-center gap-2 cursor-pointer shadow-md hover:shadow-indigo-200";
    btnStudyModalToggleDone.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i> <span>Đánh dấu đã học xong</span>`;
  }
  lucide.createIcons();
}

// --- Study Slide Viewer Logic ---

function renderTaskSlides(images) {
  state.activeSlideImages = Array.isArray(images) ? images : [];
  const total = state.activeSlideImages.length;

  if (studySlideCountBadge) {
    studySlideCountBadge.textContent = `${total} Slide`;
  }

  // If no slides for this chapter, completely hide the slides section
  if (total === 0) {
    if (studyModalSlidesSection) studyModalSlidesSection.classList.add("hidden");
    if (studySlideCarouselContainer) studySlideCarouselContainer.classList.add("hidden");
    if (studySlideScrollContainer) studySlideScrollContainer.classList.add("hidden");
    return;
  }

  // When slides are present, automatically show the section
  if (studyModalSlidesSection) studyModalSlidesSection.classList.remove("hidden");

  // Ensure active index is within bounds
  if (state.activeSlideIndex < 0 || state.activeSlideIndex >= total) {
    state.activeSlideIndex = 0;
  }

  if (state.slideViewMode === "carousel") {
    if (studySlideCarouselContainer) studySlideCarouselContainer.classList.remove("hidden");
    if (studySlideScrollContainer) studySlideScrollContainer.classList.add("hidden");

    if (btnSlideModeCarousel) {
      btnSlideModeCarousel.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 transition cursor-pointer";
    }
    if (btnSlideModeScroll) {
      btnSlideModeScroll.className = "px-2.5 py-1 rounded-lg text-[11px] font-semibold text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer";
    }

    const currentUrl = state.activeSlideImages[state.activeSlideIndex];
    if (studySlideCarouselImg) {
      studySlideCarouselImg.src = currentUrl;
    }
    if (studySlidePageIndicator) {
      studySlidePageIndicator.textContent = `Trang ${state.activeSlideIndex + 1} / ${total}`;
    }
    if (btnSlideFullscreen) {
      btnSlideFullscreen.href = currentUrl;
    }

    if (studySlideDots) {
      studySlideDots.innerHTML = state.activeSlideImages.map((_, idx) => `
        <button type="button" onclick="setSlideIndex(${idx})" class="w-2 h-2 rounded-full transition-all cursor-pointer ${
          idx === state.activeSlideIndex ? "bg-indigo-400 w-5" : "bg-slate-600 hover:bg-slate-400"
        }" title="Chuyển đến trang ${idx + 1}"></button>
      `).join("");
    }

    if (btnSlidePrev) btnSlidePrev.style.display = total <= 1 ? "none" : "flex";
    if (btnSlideNext) btnSlideNext.style.display = total <= 1 ? "none" : "flex";
  } else {
    // Vertical scroll mode
    if (studySlideCarouselContainer) studySlideCarouselContainer.classList.add("hidden");
    if (studySlideScrollContainer) studySlideScrollContainer.classList.remove("hidden");

    if (btnSlideModeScroll) {
      btnSlideModeScroll.className = "px-2.5 py-1 rounded-lg text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 transition cursor-pointer";
    }
    if (btnSlideModeCarousel) {
      btnSlideModeCarousel.className = "px-2.5 py-1 rounded-lg text-[11px] font-semibold text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer";
    }

    if (studySlideScrollContainer) {
      studySlideScrollContainer.innerHTML = state.activeSlideImages.map((url, idx) => `
        <div class="bg-slate-950 rounded-2xl p-3 sm:p-4 border border-slate-800 shadow-md space-y-2">
          <div class="flex items-center justify-between text-xs text-slate-300 px-1">
            <span class="font-bold text-indigo-400">Slide ${idx + 1} / ${total}</span>
            <a href="${url}" target="_blank" class="text-[11px] text-slate-400 hover:text-white flex items-center gap-1">
              <i data-lucide="external-link" class="w-3 h-3"></i> Xem ảnh gốc
            </a>
          </div>
          <div class="w-full flex items-center justify-center overflow-hidden min-h-[160px] max-h-[460px]">
            <img src="${url}" alt="Slide ${idx + 1}" class="max-h-[440px] max-w-full w-auto object-contain mx-auto rounded-xl shadow-lg">
          </div>
        </div>
      `).join("");
    }
  }
  lucide.createIcons();
}

window.setSlideIndex = function(idx) {
  const total = state.activeSlideImages.length;
  if (total === 0) return;
  state.activeSlideIndex = (idx + total) % total;
  renderTaskSlides(state.activeSlideImages);
};

window.nextSlide = function() {
  setSlideIndex(state.activeSlideIndex + 1);
};

window.prevSlide = function() {
  setSlideIndex(state.activeSlideIndex - 1);
};

window.switchSlideMode = function(mode) {
  state.slideViewMode = mode;
  renderTaskSlides(state.activeSlideImages);
};

function renderStudyLessonContent(lesson) {
  if (!lesson) return;

  // 1. Render 3 - 5 Core Concepts
  const concepts = lesson.core_concepts || [];
  studyModalConceptsList.innerHTML = concepts.map((c, idx) => `
    <div class="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 hover:border-indigo-200 hover:bg-indigo-50/20 transition space-y-1.5">
      <div class="flex items-center gap-2">
        <span class="w-5 h-5 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-[10px] font-black shrink-0">
          ${idx + 1}
        </span>
        <h5 class="text-xs font-bold text-slate-900">${escapeHtml(c.title || `Khái niệm ${idx + 1}`)}</h5>
      </div>
      <p class="text-xs text-slate-600 leading-relaxed pl-7">${escapeHtml(c.summary || "")}</p>
      ${c.tip ? `
        <div class="ml-7 p-2 rounded-xl bg-amber-50/80 border border-amber-200/60 text-[11px] text-amber-900 flex items-start gap-1.5">
          <span class="shrink-0 text-amber-600 font-bold">💡 Mẹo thi:</span>
          <span>${escapeHtml(c.tip)}</span>
        </div>
      ` : ""}
    </div>
  `).join("");

  // 2. Render Quick Quiz
  const quiz = lesson.quick_quiz;
  if (quiz && quiz.question) {
    studyQuizQuestion.textContent = quiz.question;
    studyQuizFeedback.classList.add("hidden");
    studyQuizFeedback.innerHTML = "";

    const options = quiz.options || [];
    studyQuizOptions.innerHTML = options.map((opt, oIdx) => `
      <button type="button" onclick="handleSelectQuizOption(${oIdx}, ${quiz.correct_index}, '${encodeURIComponent(quiz.explanation || "")}')" class="quiz-option-btn w-full p-2.5 rounded-xl border border-slate-200 bg-white hover:border-indigo-400 hover:bg-indigo-50/40 text-left text-xs text-slate-700 font-medium transition flex items-center justify-between group cursor-pointer" data-index="${oIdx}">
        <span>${escapeHtml(opt)}</span>
        <span class="w-5 h-5 rounded-full border border-slate-300 group-hover:border-indigo-500 flex items-center justify-center text-[10px] shrink-0 text-slate-400 group-hover:text-indigo-600">
          ${String.fromCharCode(65 + oIdx)}
        </span>
      </button>
    `).join("");
  } else {
    studyQuizQuestion.textContent = "Không có câu hỏi trắc nghiệm nào cho bài học này.";
    studyQuizOptions.innerHTML = "";
  }

  // 3. Render Target Goal (Advanced Materials if Advanced is selected)
  const isAdvanced = state.targetGoal === "advanced";
  const advList = lesson.advanced_materials || [];
  if (isAdvanced && advList.length > 0) {
    studyModalAdvancedSection.classList.remove("hidden");
    studyModalAdvancedList.innerHTML = advList.map((item, idx) => `
      <div class="p-3.5 rounded-2xl bg-purple-50/40 border border-purple-200/80 space-y-1">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-purple-950">${escapeHtml(item.title)}</span>
          </div>
          <span class="text-[10px] px-2 py-0.5 rounded-full bg-purple-200/70 text-purple-900 font-bold">
            ${escapeHtml(item.type || "Chuyên sâu")}
          </span>
        </div>
        <p class="text-xs text-slate-600 leading-relaxed">${escapeHtml(item.description || "")}</p>
      </div>
    `).join("");
  } else {
    studyModalAdvancedSection.classList.add("hidden");
    studyModalAdvancedList.innerHTML = "";
  }
}

window.handleSelectQuizOption = function(selectedIndex, correctIndex, encExplanation) {
  const explanation = decodeURIComponent(encExplanation || "");
  const allBtns = document.querySelectorAll(".quiz-option-btn");
  
  allBtns.forEach((btn, idx) => {
    btn.disabled = true;
    btn.classList.remove("hover:border-indigo-400", "hover:bg-indigo-50/40", "cursor-pointer");
    if (idx === correctIndex) {
      btn.className = "quiz-option-btn w-full p-2.5 rounded-xl border-2 border-emerald-500 bg-emerald-50 text-left text-xs text-emerald-900 font-bold flex items-center justify-between";
    } else if (idx === selectedIndex && selectedIndex !== correctIndex) {
      btn.className = "quiz-option-btn w-full p-2.5 rounded-xl border-2 border-rose-400 bg-rose-50 text-left text-xs text-rose-800 font-medium flex items-center justify-between";
    } else {
      btn.className = "quiz-option-btn w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-left text-xs text-slate-400 opacity-60 flex items-center justify-between";
    }
  });

  studyQuizFeedback.classList.remove("hidden");
  if (selectedIndex === correctIndex) {
    studyQuizFeedback.className = "p-3 rounded-xl bg-emerald-100/80 border border-emerald-300 text-emerald-900 text-xs font-semibold space-y-1";
    studyQuizFeedback.innerHTML = `
      <div class="flex items-center gap-1.5 font-bold text-emerald-800">
        <span class="text-sm">🎉</span> CHÍNH XÁC! Bạn đã nắm rất vững kiến thức bài này.
      </div>
      <p class="text-[11px] text-emerald-700 leading-relaxed">${escapeHtml(explanation)}</p>
    `;
    if (typeof confetti === "function") {
      confetti({ particleCount: 50, spread: 50, origin: { y: 0.7 } });
    }
  } else {
    studyQuizFeedback.className = "p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs font-semibold space-y-1";
    studyQuizFeedback.innerHTML = `
      <div class="flex items-center gap-1.5 font-bold text-rose-800">
        <span class="text-sm">💡</span> Chưa chính xác rồi!
      </div>
      <p class="text-[11px] text-slate-600 leading-relaxed">${escapeHtml(explanation)}</p>
    `;
  }
};

window.closeStudyModal = function() {
  if (studyModal) studyModal.classList.add("hidden");
  state.activeStudyTask = null;
};

window.switchStudyModalTab = function(tabName) {
  if (tabName === "lesson") {
    if (tabStudyLessonBtn) {
      tabStudyLessonBtn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 bg-indigo-50 text-indigo-700 border border-indigo-200 cursor-pointer";
    }
    if (tabStudyQaBtn) {
      tabStudyQaBtn.className = "px-3.5 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 cursor-pointer";
    }
    if (studyModalBody) studyModalBody.classList.remove("hidden");
    if (studyModalQaPane) studyModalQaPane.classList.add("hidden");
  } else {
    if (tabStudyLessonBtn) {
      tabStudyLessonBtn.className = "px-3.5 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 cursor-pointer";
    }
    if (tabStudyQaBtn) {
      tabStudyQaBtn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 bg-indigo-50 text-indigo-700 border border-indigo-200 cursor-pointer";
    }
    if (studyModalBody) studyModalBody.classList.add("hidden");
    if (studyModalQaPane) {
      studyModalQaPane.classList.remove("hidden");
      if (studyQaInput) studyQaInput.focus();
    }
  }
  lucide.createIcons();
};

async function handleStudyQaSubmit(e) {
  if (e) e.preventDefault();
  if (!state.activeStudyTask) return;
  const question = studyQaInput ? studyQaInput.value.trim() : "";
  if (!question) return;

  // Append user message
  const userBubble = document.createElement("div");
  userBubble.className = "flex items-start justify-end gap-2 text-xs";
  userBubble.innerHTML = `
    <div class="bg-indigo-600 text-white p-3 rounded-2xl rounded-tr-none max-w-[85%] shadow-xs">
      ${escapeHtml(question)}
    </div>
  `;
  studyQaMessages.appendChild(userBubble);
  studyQaInput.value = "";
  studyQaMessages.scrollTop = studyQaMessages.scrollHeight;

  // Append AI loading bubble
  const typingId = "qa-typing-" + Date.now();
  const typingBubble = document.createElement("div");
  typingBubble.id = typingId;
  typingBubble.className = "flex items-start gap-2 text-xs";
  typingBubble.innerHTML = `
    <div class="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5">
      <i data-lucide="bot" class="w-3.5 h-3.5"></i>
    </div>
    <div class="bg-slate-100 p-3 rounded-2xl rounded-tl-none border border-slate-200 text-slate-500 max-w-[85%] animate-pulse">
      <span class="inline-block animate-spin mr-1">✨</span> Đang đối chiếu tài liệu để giải đáp...
    </div>
  `;
  studyQaMessages.appendChild(typingBubble);
  studyQaMessages.scrollTop = studyQaMessages.scrollHeight;
  lucide.createIcons();

  if (btnStudyQaSend) btnStudyQaSend.disabled = true;

  try {
    const res = await fetch(`/api/tasks/${state.activeStudyTask.id}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({
        question: question,
        gemini_api_key: state.geminiApiKey || null
      })
    });

    const curTyping = document.getElementById(typingId);
    if (curTyping) curTyping.remove();

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Không thể trả lời câu hỏi.");
    }

    const data = await res.json();
    const renderedAnswer = marked.parse(data.answer);

    const aiBubble = document.createElement("div");
    aiBubble.className = "flex items-start gap-2 text-xs";
    aiBubble.innerHTML = `
      <div class="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
        <i data-lucide="bot" class="w-3.5 h-3.5"></i>
      </div>
      <div class="bg-white p-3.5 rounded-2xl rounded-tl-none border border-slate-200 text-slate-800 max-w-[85%] shadow-xs leading-relaxed prose prose-xs">
        ${renderedAnswer}
      </div>
    `;
    studyQaMessages.appendChild(aiBubble);
  } catch (err) {
    const curTyping = document.getElementById(typingId);
    if (curTyping) curTyping.remove();

    const errBubble = document.createElement("div");
    errBubble.className = "flex items-start gap-2 text-xs";
    errBubble.innerHTML = `
      <div class="w-6 h-6 rounded-full bg-rose-600 text-white flex items-center justify-center shrink-0 mt-0.5">
        ⚠️
      </div>
      <div class="bg-rose-50 p-3 rounded-2xl rounded-tl-none border border-rose-200 text-rose-800 max-w-[85%]">
        Lỗi: ${escapeHtml(err.message)}
      </div>
    `;
    studyQaMessages.appendChild(errBubble);
  } finally {
    if (btnStudyQaSend) btnStudyQaSend.disabled = false;
    studyQaMessages.scrollTop = studyQaMessages.scrollHeight;
    lucide.createIcons();
  }
}

window.handleToggleTask = async function(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/toggle`, { method: "PATCH" });
    if (!res.ok) throw new Error("Không thể cập nhật trạng thái nhiệm vụ.");
    
    // Refresh plan
    const planRes = await fetch(`/api/plans/${state.currentPlanId}`);
    const planData = await planRes.json();
    renderPlanDashboard(planData);

    // If 100% completed, throw confetti!
    if (planData.progress_percent === 100 && typeof confetti === "function") {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 }
      });
    }
  } catch (err) {
    alert("Lỗi: " + err.message);
  }
};

// --- Reschedule Action ---
async function handleReschedule() {
  if (!state.currentPlanId) return;

  if (!confirm("Bạn có chắc muốn tái tạo lại lộ trình? Các bài học chưa hoàn thành từ hôm nay trở về trước sẽ được tự động dồn và phân bổ đều vào các ngày còn lại!")) {
    return;
  }

  btnReschedule.disabled = true;
  btnReschedule.innerHTML = `<span class="animate-spin mr-1">⏳</span> Đang tính toán dồn lịch...`;

  try {
    const res = await fetch(`/api/plans/${state.currentPlanId}/reschedule`, { method: "POST" });
    if (!res.ok) throw new Error("Không thể tái tạo lộ trình.");
    const planData = await res.json();
    renderPlanDashboard(planData);
    alert("✨ Tuyệt vời! AI đã dồn các bài trễ và phân bổ lại lịch học tối ưu từ hôm nay!");
  } catch (err) {
    alert("Lỗi: " + err.message);
  } finally {
    btnReschedule.disabled = false;
    btnReschedule.innerHTML = `<i data-lucide="refresh-cw" class="w-4 h-4 mr-1.5 text-amber-700"></i> ⚡ Tôi Bị Lỡ Bài - Tái Tạo Lộ Trình`;
    lucide.createIcons();
  }
}

// --- AI Chatbot RAG ---
async function handleSendMessage(e) {
  if (e && e.preventDefault) e.preventDefault();
  const q = chatInput.value.trim();
  if (!q) return;

  if (!state.currentDocId) {
    alert("Vui lòng tải lên đề cương trước khi hỏi đáp với AI!");
    return;
  }

  // Append user bubble
  appendChatBubble("user", q);
  chatInput.value = "";

  // Append typing indicator
  const typingId = "typing-" + Date.now();
  const typingElem = document.createElement("div");
  typingElem.id = typingId;
  typingElem.className = "flex items-start gap-2 text-slate-400 italic text-[11px]";
  typingElem.innerHTML = `<span>🤖 Gia sư AI đang tra cứu tài liệu và soạn câu trả lời...</span>`;
  chatMessages.appendChild(typingElem);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const res = await fetch("/api/chat/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: state.currentDocId,
        question: q,
        gemini_api_key: state.geminiApiKey || null
      })
    });

    if (!res.ok) throw new Error("Lỗi khi kết nối với trợ lý AI.");
    const data = await res.json();
    
    // Remove typing indicator
    const curTyping = document.getElementById(typingId);
    if (curTyping) curTyping.remove();

    appendChatBubble("assistant", data.answer);
  } catch (err) {
    const curTyping = document.getElementById(typingId);
    if (curTyping) curTyping.remove();
    appendChatBubble("assistant", "⚠️ Lỗi: " + err.message);
  }
}

function appendChatBubble(role, content) {
  const wrapper = document.createElement("div");
  if (role === "user") {
    wrapper.className = "flex items-start justify-end gap-2.5";
    wrapper.innerHTML = `
      <div class="bg-indigo-600 text-white p-3 rounded-2xl rounded-tr-none max-w-[85%] shadow-sm">
        ${escapeHtml(content)}
      </div>
    `;
  } else {
    wrapper.className = "flex items-start gap-2.5";
    const renderedHtml = marked.parse(content);
    wrapper.innerHTML = `
      <div class="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5">
        <i data-lucide="bot" class="w-3.5 h-3.5"></i>
      </div>
      <div class="bg-white p-3 rounded-2xl rounded-tl-none border border-slate-200 text-slate-700 max-w-[85%] shadow-sm leading-relaxed prose prose-xs">
        ${renderedHtml}
      </div>
    `;
  }

  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  lucide.createIcons();
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
