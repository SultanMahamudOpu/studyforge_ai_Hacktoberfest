const state = {
  tutor: "",
  planner: "",
  quiz: null,
  pdfFileId: null,
};

const $ = (id) => document.getElementById(id);

// =========================================================
// TOAST
// =========================================================

function toast(message) {
  const el = $("toast");

  if (!el) return;

  el.textContent = message;
  el.classList.add("show");

  clearTimeout(window.__toast);

  window.__toast = setTimeout(() => {
    el.classList.remove("show");
  }, 3000);
}

// =========================================================
// API HELPER
// =========================================================

async function api(url, options = {}) {
  let response;

  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(
      "Unable to connect to the server. Please try again."
    );
  }

  const type =
    response.headers.get("content-type") || "";

  if (!response.ok) {
    let message =
      `Request failed (${response.status}).`;

    try {
      if (type.includes("application/json")) {
        const data = await response.json();

        message =
          data.error ||
          data.message ||
          message;
      } else {
        const text = await response.text();

        if (text) {
          message = text.slice(0, 500);
        }
      }
    } catch (_) {
      // Keep default error message.
    }

    throw new Error(message);
  }

  if (type.includes("application/json")) {
    return await response.json();
  }

  return await response.blob();
}

// =========================================================
// HTML ESCAPE
// =========================================================

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// =========================================================
// MARKDOWN RENDERER
// =========================================================

function markdownToHtml(md) {
  let html = escapeHtml(md);

  // Code blocks
  html = html.replace(
    /```([\s\S]*?)```/g,
    (_, code) => `<pre>${code.trim()}</pre>`
  );

  // Headings
  html = html.replace(
    /^### (.*)$/gm,
    "<h3>$1</h3>"
  );

  html = html.replace(
    /^## (.*)$/gm,
    "<h2>$1</h2>"
  );

  html = html.replace(
    /^# (.*)$/gm,
    "<h1>$1</h1>"
  );

  // Lists
  html = html.replace(
    /^\s*[-*] (.*)$/gm,
    "<li>$1</li>"
  );

  html = html.replace(
    /(<li>.*?<\/li>\s*)+/gs,
    (block) => `<ul>${block}</ul>`
  );

  // Bold
  html = html.replace(
    /\*\*(.*?)\*\*/g,
    "<strong>$1</strong>"
  );

  // Inline code
  html = html.replace(
    /`([^`]+)`/g,
    "<code>$1</code>"
  );

  // Paragraphs
  html = html
    .split(/\n{2,}/)
    .map((part) => {
      const trimmed = part.trim();

      if (!trimmed) {
        return "";
      }

      if (
        /^<(h1|h2|h3|ul|pre)/.test(trimmed)
      ) {
        return trimmed;
      }

      return `<p>${trimmed.replace(
        /\n/g,
        "<br>"
      )}</p>`;
    })
    .join("");

  return html;
}

// =========================================================
// NAVIGATION
// =========================================================

function showSection(id) {
  document
    .querySelectorAll(".section")
    .forEach((section) => {
      section.classList.remove("active");
    });

  document
    .querySelectorAll(".nav-item")
    .forEach((nav) => {
      nav.classList.remove("active");
    });

  const section = $(id);

  if (!section) {
    return;
  }

  section.classList.add("active");

  document
    .querySelector(
      `.nav-item[data-section="${id}"]`
    )
    ?.classList.add("active");

  const titles = {
    dashboard: "Dashboard",
    tutor: "AI Tutor",
    planner: "Study Planner",
    quiz: "Smart Quiz",
    pdf: "PDF Reader",
  };

  const pageTitle = $("pageTitle");

  if (pageTitle) {
    pageTitle.textContent =
      titles[id] || "StudyForge";
  }

  $("sidebar")?.classList.remove("open");

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

document
  .querySelectorAll(".nav-item")
  .forEach((btn) => {
    btn.addEventListener("click", () => {
      showSection(btn.dataset.section);
    });
  });

document
  .querySelectorAll("[data-go]")
  .forEach((btn) => {
    btn.addEventListener("click", () => {
      showSection(btn.dataset.go);
    });
  });

$("menuBtn")?.addEventListener("click", () => {
  $("sidebar")?.classList.toggle("open");
});

$("themeBtn")?.addEventListener("click", () => {
  document.body.classList.toggle("dark");

  localStorage.setItem(
    "studyforge-dark",
    document.body.classList.contains("dark")
      ? "1"
      : "0"
  );
});

if (
  localStorage.getItem("studyforge-dark") === "1"
) {
  document.body.classList.add("dark");
}

// =========================================================
// LOADING
// =========================================================

function setLoading(name, value) {
  const loader = $(name + "Loader");

  if (!loader) {
    return;
  }

  loader.classList.toggle(
    "hidden",
    !value
  );
}

// =========================================================
// AI TUTOR
// =========================================================

$("tutorForm")?.addEventListener(
  "submit",
  async (e) => {
    e.preventDefault();

    setLoading("tutor", true);

    $("tutorResult")?.classList.add(
      "empty-state"
    );

    try {
      const data = await api(
        "/api/tutor",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            topic:
              $("tutorTopic")?.value || "",

            level:
              $("tutorLevel")?.value || "",

            language:
              $("tutorLanguage")?.value || "",

            follow_up:
              $("tutorFollowUp")?.value || "",
          }),
        }
      );

      state.tutor =
        data.content || "";

      $("tutorResult")?.classList.remove(
        "empty-state"
      );

      if ($("tutorResult")) {
        $("tutorResult").innerHTML =
          markdownToHtml(state.tutor);
      }

      toast("Lesson generated.");
    } catch (err) {
      toast(
        err.message ||
        "Failed to generate lesson."
      );
    } finally {
      setLoading("tutor", false);
    }
  }
);

// =========================================================
// STUDY PLANNER
// =========================================================

$("plannerForm")?.addEventListener(
  "submit",
  async (e) => {
    e.preventDefault();

    setLoading("planner", true);

    $("plannerResult")?.classList.add(
      "empty-state"
    );

    try {
      const data = await api(
        "/api/study-plan",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            topic:
              $("planTopic")?.value || "",

            minutes:
              $("planMinutes")?.value || "",

            days:
              $("planDays")?.value || "",

            level:
              $("planLevel")?.value || "",

            language:
              $("planLanguage")?.value || "",
          }),
        }
      );

      state.planner =
        data.content || "";

      $("plannerResult")?.classList.remove(
        "empty-state"
      );

      if ($("plannerResult")) {
        $("plannerResult").innerHTML =
          markdownToHtml(state.planner);
      }

      toast("Study plan ready.");
    } catch (err) {
      toast(
        err.message ||
        "Failed to create study plan."
      );
    } finally {
      setLoading("planner", false);
    }
  }
);

// =========================================================
// QUIZ
// =========================================================

$("quizForm")?.addEventListener(
  "submit",
  async (e) => {
    e.preventDefault();

    const button =
      $("quizForm").querySelector(
        'button[type="submit"]'
      );

    // Show loading state
    if (button) {
      button.disabled = true;

      button.textContent =
        "⏳ Generating Quiz... Please wait";
    }

    // Tell user to wait
    toast(
      "Quiz is being generated. Please wait..."
    );

    try {
      const data = await api(
        "/api/quiz",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            topic:
              $("quizTopic")?.value || "",

            difficulty:
              $("quizDifficulty")?.value || "",

            count:
              $("quizCount")?.value || "",

            language:
              $("quizLanguage")?.value || "",
          }),
        }
      );

      if (
        !data.quiz ||
        !Array.isArray(
          data.quiz.questions
        )
      ) {
        throw new Error(
          "Invalid quiz data received."
        );
      }

      state.quiz = data.quiz;

      renderQuiz(data.quiz);

      $("quizResults")?.classList.add(
        "hidden"
      );

      toast("Quiz generated.");
    } catch (err) {
      toast(
        err.message ||
        "Failed to generate quiz."
      );
    } finally {
      // Restore button
      if (button) {
        button.disabled = false;

        button.textContent =
          "Generate Quiz ✓";
      }
    }
  }
);

// =========================================================
// RENDER QUIZ
// =========================================================

function renderQuiz(quiz) {
  if (!quiz || !Array.isArray(quiz.questions)) {
    return;
  }

  $("quizArea")?.classList.remove(
    "hidden"
  );

  if ($("quizTitle")) {
    $("quizTitle").textContent =
      quiz.title || "Smart Quiz";
  }

  if ($("quizProgress")) {
    $("quizProgress").textContent =
      `0 / ${quiz.questions.length}`;
  }

  const questionsContainer =
    $("quizQuestions");

  if (!questionsContainer) {
    return;
  }

  questionsContainer.innerHTML =
    quiz.questions
      .map(
        (q, i) => `
          <div
            class="question-card"
            data-q="${i}"
          >
            <h4>
              ${i + 1}.
              ${escapeHtml(q.question)}
            </h4>

            ${q.options
              .map(
                (opt, j) => `
                  <label
                    class="option"
                    data-option="${j}"
                  >
                    <input
                      type="radio"
                      name="q${i}"
                      value="${j}"
                    >

                    <span>
                      ${escapeHtml(opt)}
                    </span>
                  </label>
                `
              )
              .join("")}

            <div
              class="explanation hidden"
              id="explanation-${i}"
            ></div>
          </div>
        `
      )
      .join("");

  questionsContainer
    .querySelectorAll("input")
    .forEach((input) => {
      input.addEventListener(
        "change",
        () => {
          const answered =
            [
              ...document.querySelectorAll(
                "#quizQuestions input:checked"
              ),
            ].length;

          if ($("quizProgress")) {
            $("quizProgress").textContent =
              `${answered} / ${quiz.questions.length}`;
          }
        }
      );
    });
}

// =========================================================
// SUBMIT QUIZ
// =========================================================

$("quizSubmitForm")?.addEventListener(
  "submit",
  (e) => {
    e.preventDefault();

    if (!state.quiz) {
      return;
    }

    let score = 0;

    state.quiz.questions.forEach(
      (q, i) => {
        const card =
          document.querySelector(
            `[data-q="${i}"]`
          );

        if (!card) {
          return;
        }

        const selected =
          card.querySelector(
            "input:checked"
          );

        const options = [
          ...card.querySelectorAll(
            ".option"
          ),
        ];

        options.forEach(
          (option, j) => {
            option.classList.remove(
              "correct",
              "incorrect"
            );

            if (j === q.answer) {
              option.classList.add(
                "correct"
              );
            }
          }
        );

        if (selected) {
          const chosen =
            Number(
              selected.value
            );

          if (
            chosen === q.answer
          ) {
            score++;
          } else if (
            options[chosen]
          ) {
            options[chosen].classList.add(
              "incorrect"
            );
          }
        }

        const explanation =
          $(
            `explanation-${i}`
          );

        if (explanation) {
          explanation.classList.remove(
            "hidden"
          );

          explanation.innerHTML =
            `<strong>Explanation:</strong> ${escapeHtml(
              q.explanation
            )}`;
        }
      }
    );

    const total =
      state.quiz.questions.length;

    const percent =
      total > 0
        ? Math.round(
            (score / total) * 100
          )
        : 0;

    $("quizResults")?.classList.remove(
      "hidden"
    );

    if ($("quizResults")) {
      $("quizResults").innerHTML = `
        <h3>
          ${score} / ${total} correct
        </h3>

        <p>
          ${percent}% score.
          Review the explanations above
          and try the quiz again.
        </p>
      `;
    }

    $("quizResults")?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }
);

// =========================================================
// DOWNLOAD BLOB
// =========================================================

function downloadBlob(blob, filename) {
  if (!blob || blob.size === 0) {
    throw new Error(
      "The server returned an empty file."
    );
  }

  const url =
    URL.createObjectURL(blob);

  const link =
    document.createElement("a");

  link.href = url;

  link.download =
    filename || "studyforge.pdf";

  document.body.appendChild(link);

  link.click();

  link.remove();

  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 1000);
}

// =========================================================
// PDF EXPORT
// =========================================================

async function exportContent(kind) {
  const content = state[kind];

  if (!content) {
    return toast(
      "Generate some content first."
    );
  }

  const title =
    kind === "tutor"
      ? (
          $("tutorTopic")?.value ||
          "AI Tutor Lesson"
        )
      : (
          $("planTopic")?.value ||
          "Study Plan"
        );

  try {
    toast("Preparing PDF...");

    const blob = await api(
      "/api/export/pdf",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          title,
          content,
        }),
      }
    );

    if (!(blob instanceof Blob)) {
      throw new Error(
        "Invalid PDF response."
      );
    }

    const filename =
      `${title
        .replace(
          /[^a-z0-9]+/gi,
          "-"
        )
        .replace(
          /^-+|-+$/g,
          ""
        )
        .slice(0, 80) ||
        "studyforge-document"}.pdf`;

    downloadBlob(
      blob,
      filename
    );

    toast("PDF downloaded.");
  } catch (err) {
    toast(
      err.message ||
      "PDF export failed."
    );
  }
}

// =========================================================
// TEXT TO SPEECH
// =========================================================

let currentAudio = null;
let currentAudioUrl = null;

async function playAudio(kind) {
  const content = state[kind];

  if (!content) {
    return toast(
      "Generate some content first."
    );
  }

  try {
    toast("Generating audio...");

    // Stop previous audio
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    // Revoke previous URL
    if (currentAudioUrl) {
      URL.revokeObjectURL(
        currentAudioUrl
      );

      currentAudioUrl = null;
    }

    const blob = await api(
      "/api/tts",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          text: content,
        }),
      }
    );

    if (!(blob instanceof Blob)) {
      throw new Error(
        "Invalid audio response."
      );
    }

    if (blob.size === 0) {
      throw new Error(
        "The server returned empty audio."
      );
    }

    currentAudioUrl =
      URL.createObjectURL(blob);

    currentAudio =
      new Audio(
        currentAudioUrl
      );

    currentAudio.preload = "auto";

    currentAudio.addEventListener(
      "ended",
      () => {
        if (currentAudioUrl) {
          URL.revokeObjectURL(
            currentAudioUrl
          );

          currentAudioUrl = null;
        }

        currentAudio = null;
      },
      {
        once: true,
      }
    );

    await currentAudio.play();

    toast(
      "Playing ElevenLabs audio."
    );
  } catch (err) {
    toast(
      err.message ||
      "Audio generation failed."
    );
  }
}

// =========================================================
// EXPORT + AUDIO BUTTONS
// =========================================================

document
  .querySelectorAll("[data-export]")
  .forEach((btn) => {
    btn.addEventListener(
      "click",
      () => {
        exportContent(
          btn.dataset.export
        );
      }
    );
  });

document
  .querySelectorAll("[data-audio]")
  .forEach((btn) => {
    btn.addEventListener(
      "click",
      () => {
        playAudio(
          btn.dataset.audio
        );
      }
    );
  });

// =========================================================
// PDF UPLOAD
// =========================================================

$("choosePdf")?.addEventListener(
  "click",
  () => {
    $("pdfInput")?.click();
  }
);

$("pdfInput")?.addEventListener(
  "change",
  (e) => {
    if (e.target.files[0]) {
      uploadPdf(
        e.target.files[0]
      );
    }
  }
);

// Drag & Drop - Enter / Over
["dragenter", "dragover"].forEach(
  (event) => {
    $("dropZone")?.addEventListener(
      event,
      (e) => {
        e.preventDefault();

        $("dropZone")?.classList.add(
          "drag"
        );
      }
    );
  }
);

// Drag & Drop - Leave / Drop
["dragleave", "drop"].forEach(
  (event) => {
    $("dropZone")?.addEventListener(
      event,
      (e) => {
        e.preventDefault();

        $("dropZone")?.classList.remove(
          "drag"
        );
      }
    );
  }
);

// Drop file
$("dropZone")?.addEventListener(
  "drop",
  (e) => {
    const file =
      e.dataTransfer.files[0];

    if (file) {
      uploadPdf(file);
    }
  }
);

// =========================================================
// UPLOAD PDF
// =========================================================

async function uploadPdf(file) {
  if (
    file.type !== "application/pdf" &&
    !file.name
      .toLowerCase()
      .endsWith(".pdf")
  ) {
    return toast(
      "Please upload a PDF."
    );
  }

  const form =
    new FormData();

  form.append(
    "file",
    file
  );

  if ($("fileStatus")) {
    $("fileStatus").textContent =
      "Uploading and reading...";
  }

  try {
    const data = await api(
      "/api/pdf/upload",
      {
        method: "POST",
        body: form,
      }
    );

    state.pdfFileId =
      data.file_id;

    if ($("fileStatus")) {
      $("fileStatus").textContent =
        `${data.filename} · ${data.chunks} chunks`;
    }

    if ($("chatDocName")) {
      $("chatDocName").textContent =
        data.filename;
    }

    if ($("pdfQuestion")) {
      $("pdfQuestion").disabled = false;
    }

    if ($("pdfAskBtn")) {
      $("pdfAskBtn").disabled = false;
    }

    toast("PDF loaded.");
  } catch (err) {
    if ($("fileStatus")) {
      $("fileStatus").textContent =
        "Upload failed";
    }

    toast(
      err.message ||
      "PDF upload failed."
    );
  }
}

// =========================================================
// PDF CHAT
// =========================================================

$("pdfChatForm")?.addEventListener(
  "submit",
  async (e) => {
    e.preventDefault();

    if (!state.pdfFileId) {
      return toast(
        "Upload a PDF first."
      );
    }

    const question =
      $("pdfQuestion")?.value
        ?.trim() || "";

    if (!question) {
      return;
    }

    addChatBubble(
      "user",
      question
    );

    if ($("pdfQuestion")) {
      $("pdfQuestion").value = "";
    }

    if ($("pdfAskBtn")) {
      $("pdfAskBtn").disabled = true;
    }

    try {
      const data = await api(
        "/api/pdf/chat",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            file_id:
              state.pdfFileId,

            question,
          }),
        }
      );

      if (
        data.answer ===
        "NOT_FOUND_IN_PDF"
      ) {
        addChatBubble(
          "assistant",
          "I couldn't find that information in the uploaded PDF."
        );
      } else {
        addChatBubble(
          "assistant",
          data.answer
        );
      }
    } catch (err) {
      addChatBubble(
        "assistant",
        `Error: ${err.message}`
      );
    } finally {
      if ($("pdfAskBtn")) {
        $("pdfAskBtn").disabled = false;
      }
    }
  }
);

// =========================================================
// CHAT BUBBLE
// =========================================================

function addChatBubble(role, text) {
  const wrap =
    document.createElement(
      "div"
    );

  wrap.className =
    `chat-bubble ${role}`;

  wrap.innerHTML = `
    <strong>
      ${
        role === "user"
          ? "You"
          : "StudyForge"
      }
    </strong>

    <p>
      ${escapeHtml(text)}
    </p>
  `;

  $("chatMessages")?.appendChild(
    wrap
  );

  const chatMessages =
    $("chatMessages");

  if (chatMessages) {
    chatMessages.scrollTop =
      chatMessages.scrollHeight;
  }
}

// =========================================================
// HEALTH CHECK
// =========================================================

async function checkHealth() {
  try {
    const data =
      await api(
        "/api/health"
      );

    if (!$("service-status")) {
      return;
    }

    $("service-status").textContent =
      data.gemma_configured &&
      data.elevenlabs_configured
        ? "Gemma + ElevenLabs ready"
        : "Add API keys";
  } catch (_) {
    if ($("service-status")) {
      $("service-status").textContent =
        "Offline";
    }
  }
}

// =========================================================
// INITIALIZE
// =========================================================

checkHealth();