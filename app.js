// ===== Validation settings =====
const MAX_FILE_SIZE_MB = 10;
const ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "webp"];

// ✅ Your FastAPI endpoint
const API_URL = "http://127.0.0.1:8000/predict"; // change later when hosting online

// ===== Elements =====
const imageInput = document.getElementById("imageInput");
const previewImg = document.getElementById("previewImg");
const fileNameEl = document.getElementById("fileName");
const fileSizeEl = document.getElementById("fileSize");
const statusPill = document.getElementById("statusPill");

const analyzeBtn = document.getElementById("analyzeBtn");
const resetBtn = document.getElementById("resetBtn");

const resultBadge = document.getElementById("resultBadge");
const resultTitle = document.getElementById("resultTitle");
const resultSummary = document.getElementById("resultSummary");
const observationsEl = document.getElementById("observations");
const tipsEl = document.getElementById("tips");
const remarksText = document.getElementById("remarksText");

let selectedFile = null;

// ===== Authentication Helper =====
function getAuthToken() {
  return localStorage.getItem('access_token');
}

function isAuthenticated() {
  return !!getAuthToken();
}

function redirectToLogin() {
  window.location.href = '/login.html';
}

function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  redirectToLogin();
}

// Check authentication on page load
window.addEventListener('DOMContentLoaded', () => {
  if (!isAuthenticated()) {
    redirectToLogin();
  }
  
  // Display user info if available
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  if (user.first_name) {
    const statusText = `Welcome, ${user.first_name}`;
    statusPill.textContent = statusText;
  }
});

// ===== Helpers =====
function bytesToSize(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) {
    n = n / 1024;
    i++;
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function setList(el, items) {
  el.innerHTML = "";
  items.forEach((t) => {
    const li = document.createElement("li");
    li.textContent = t;
    el.appendChild(li);
  });
}

function setStatus(text) {
  statusPill.textContent = text;
}

function setWaitingUI() {
  resultBadge.textContent = "Waiting…";
  resultBadge.style.borderColor = "rgba(255,255,255,0.14)";
  resultBadge.style.background = "rgba(255,255,255,0.05)";

  resultTitle.textContent = "Upload an image to begin";
  resultSummary.textContent =
    "Select a photo and press Analyze. The AI model will run on your image.";

  setList(observationsEl, ["—"]);
  setList(tipsEl, ["—"]);
  remarksText.textContent = "—";
}

function setAnalyzingUI() {
  resultBadge.textContent = "Analyzing…";
  resultBadge.style.borderColor = "rgba(255,255,255,0.14)";
  resultBadge.style.background = "rgba(255,255,255,0.05)";

  resultTitle.textContent = "Processing image";
  resultSummary.textContent =
    "Uploading image to AI server and running inference…";

  setList(observationsEl, [
    "Preprocessing image…",
    "Running model…",
    "Computing confidence…",
  ]);
  setList(tipsEl, ["—"]);
  remarksText.textContent = "Finalizing report…";
}

function showError(message) {
  resultBadge.textContent = "Error ❌";
  resultBadge.style.borderColor = "rgba(239,68,68,0.55)";
  resultBadge.style.background = "rgba(239,68,68,0.14)";

  resultTitle.textContent = "Something went wrong";
  resultSummary.textContent = message;

  setList(observationsEl, []);
  setList(tipsEl, []);
  remarksText.textContent = "Please try again with a valid image.";

  setStatus("Error ❌");
}

function formatPercent(x) {
  return `${(x * 100).toFixed(1)}%`;
}

function setResultFromModel(predClass, confidence) {
  const cls = String(predClass).toLowerCase();
  const isHealthy = (cls === "healthy" || cls.includes("healthy"));

  if (isHealthy) {
    resultBadge.textContent = "Healthy ✅";
    resultBadge.style.borderColor = "rgba(34,197,94,0.45)";
    resultBadge.style.background = "rgba(34,197,94,0.14)";

    resultTitle.textContent = "Leaf looks healthy";
    resultSummary.textContent = `Model confidence: ${formatPercent(confidence)}.`;

    setList(observationsEl, [
      "No strong disease pattern detected by the model.",
      "Color/texture appear consistent with healthy tissue.",
    ]);

    setList(tipsEl, [
      "Keep watering consistent.",
      "Maintain airflow to reduce humidity-related issues.",
      "Monitor weekly for new spots or curling.",
    ]);

    remarksText.textContent =
      "AI output is probabilistic. If symptoms spread fast, take multiple photos and consider expert advice.";
    return;
  }

  resultBadge.textContent = "Unhealthy ⚠️";
  resultBadge.style.borderColor = "rgba(239,68,68,0.55)";
  resultBadge.style.background = "rgba(239,68,68,0.14)";

  resultTitle.textContent = `Detected: ${predClass}`;
  resultSummary.textContent = `Model confidence: ${formatPercent(confidence)}.`;

  // simple disease-specific tips (edit later if you want)
  const tipsByDisease = {
    early_blight: [
      "Remove heavily affected leaves.",
      "Avoid overhead watering (water soil only).",
      "Improve airflow; avoid overcrowding.",
      "Consider plant-safe fungicide if it spreads.",
    ],
    late_blight: [
      "Act quickly: late blight can spread fast.",
      "Remove infected leaves and isolate plant if possible.",
      "Keep foliage dry; avoid overhead watering.",
      "Monitor daily; consider appropriate fungicide.",
    ],
    tomato_yellow_leaf_curl_virus: [
      "Check for whiteflies (common vector).",
      "Use netting/sticky traps if needed.",
      "Remove severely affected leaves/plant if worsening.",
      "Reduce stress: stable watering & nutrients.",
    ],
  };

  // normalize model class name to a key
  let key = cls;
  if (cls.includes("yellow_leaf") || cls.includes("curl_virus")) key = "tomato_yellow_leaf_curl_virus";
  if (cls.includes("early")) key = "early_blight";
  if (cls.includes("late")) key = "late_blight";

  setList(observationsEl, [
    `The model predicts "${predClass}".`,
    "Take multiple photos (different angles/light) for better confidence.",
  ]);

  setList(tipsEl, tipsByDisease[key] ?? [
    "Take 2–3 more photos in different lighting.",
    "Inspect underside of leaves for pests.",
    "Reduce leaf moisture and improve airflow.",
  ]);

  remarksText.textContent =
    "AI can be wrong. Confirm with additional symptoms or expert guidance if needed.";
}

// ===== Events =====
imageInput.addEventListener("change", (e) => {
  const file = e.target.files?.[0];

  if (!file) {
    setStatus("No image selected");
    showError("Image is mandatory. Please upload a leaf image.");
    return;
  }

  const fileName = file.name.toLowerCase();
  const extension = fileName.includes(".") ? fileName.split(".").pop() : "";

  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    imageInput.value = "";
    setStatus("Invalid file ❌");
    showError("Please upload a JPG, JPEG, PNG, or WebP file.");
    return;
  }

  const sizeMB = file.size / (1024 * 1024);
  if (sizeMB > MAX_FILE_SIZE_MB) {
    imageInput.value = "";
    setStatus("File too large ❌");
    showError("Image is too large. Maximum allowed size is 10 MB.");
    return;
  }

  selectedFile = file;

  fileNameEl.textContent = file.name;
  fileSizeEl.textContent = bytesToSize(file.size);

  const url = URL.createObjectURL(file);
  previewImg.src = url;
  previewImg.style.display = "block";

  analyzeBtn.disabled = false;
  resetBtn.disabled = false;

  setStatus("Image selected ✅");
  setWaitingUI();
});

resetBtn.addEventListener("click", () => {
  selectedFile = null;
  imageInput.value = "";

  previewImg.removeAttribute("src");
  previewImg.style.display = "none";

  fileNameEl.textContent = "—";
  fileSizeEl.textContent = "—";

  analyzeBtn.disabled = true;
  resetBtn.disabled = true;

  setStatus("No image selected");
  setWaitingUI();
});

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    setStatus("No image selected");
    showError("Image is mandatory. Please upload a leaf image.");
    return;
  }

  // Check authentication
  if (!isAuthenticated()) {
    showError("You must be logged in to analyze images.");
    setTimeout(redirectToLogin, 2000);
    return;
  }

  setStatus("Analyzing…");
  setAnalyzingUI();
  analyzeBtn.disabled = true;

  try {
    const fd = new FormData();
    fd.append("file", selectedFile);

    const token = getAuthToken();
    
    const res = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      },
      credentials: "include",  // Send cookies for dual auth support
      body: fd,
    });

    if (res.status === 401) {
      // Token expired or invalid
      logout();
      throw new Error("Session expired. Please login again.");
    }

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API error ${res.status}: ${text || "Unknown error"}`);
    }

    const data = await res.json(); // { class: "...", confidence: 0.92 }
    setStatus("Analysis complete ✅");
    setResultFromModel(data.class, data.confidence);

  } catch (err) {
    console.error(err);
    showError(err.message || "Could not reach the AI server. Check API_URL / server running / CORS.");
  } finally {
    analyzeBtn.disabled = false;
  }
});

// Init
analyzeBtn.disabled = true;
resetBtn.disabled = true;
setStatus("No image selected");
setWaitingUI();
