// UI Elements
const chatBox = document.getElementById("chatbot");
const chatIcon = document.getElementById("chatIcon");
const closeBtn = document.getElementById("closeChatbot");
const input = document.getElementById("chat-message-input");
const sendBtn = document.getElementById("chat-message-submit");
const clearBtn = document.getElementById("chat-message-clear");
const chatLog = document.getElementById("chat-log");
const loader = document.getElementById("loading");
const quickCommands = document.querySelectorAll(".quick-command");

if (!chatBox || !chatIcon || !closeBtn || !input || !sendBtn || !chatLog) {
  throw new Error("Required chatbot elements missing");
}

// Welcome message flag
let hasWelcomed = false;

// Toggle open
chatIcon.addEventListener("click", () => {
  chatBox.classList.remove("hidden");
  // Show welcome message on first open
  if (!hasWelcomed) {
    addBotMessage(
      "Hello! I'm BLT Bot. How can I help you today? Try using the quick commands below or type your question!"
    );
    hasWelcomed = true;
  }
});

// Close panel
closeBtn.addEventListener("click", () => {
  chatBox.classList.add("hidden");
});

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Add messages
function addUserMessage(text) {
  const escapedText = escapeHtml(text);
  chatLog.innerHTML += `
        <div class="my-2 text-right">
            <div class="inline-block bg-green-100 dark:bg-green-800 p-2 rounded-lg text-black dark:text-white">
                <b>You -</b> ${escapedText}
            </div>
        </div>
    `;
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addBotMessage(text) {
  const escapedText = escapeHtml(text);
  chatLog.innerHTML += `
        <div class="my-2">
            <div class="inline-block bg-blue-100 dark:bg-blue-800 p-2 rounded-lg text-black dark:text-white">
                <b>Bot -</b> ${escapedText}
            </div>
        </div>
    `;
  chatLog.scrollTop = chatLog.scrollHeight;
}

function showLoader() {
  loader.classList.remove("hidden");
}

function hideLoader() {
  loader.classList.add("hidden");
}

// Sending user message
sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keypress", function (e) {
  if (e.key === "Enter") sendMessage();
});

// CLEAR CHAT
clearBtn.addEventListener("click", () => {
  chatLog.innerHTML = "";
  hasWelcomed = false; // Reset welcome flag so it shows again on next open
});

// Quick command buttons
quickCommands.forEach((button) => {
  button.addEventListener("click", () => {
    const command = button.getAttribute("data-command");
    if (command) {
      input.value = command;
      sendMessage();
    }
  });
});

// --- MAIN FUNCTION ---
async function sendMessage() {
  let message = input.value.trim();
  if (!message) return;

  addUserMessage(message);
  input.value = "";
  showLoader();

  try {
    let response = await fetch("/api/chatbot/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    let data = await response.json();
    hideLoader();

    if (data.reply) {
      addBotMessage(data.reply);
    } else {
      addBotMessage(
        "I received your message, but couldn't generate a response. Please try again."
      );
    }
  } catch (error) {
    hideLoader();

    addBotMessage(
      "Error connecting to server. Please check your connection and try again."
    );
  }
}

// Extract CSRF token
function getCSRFToken() {
  let cookieValue = null;
  let cookies = document.cookie.split(";");

  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith("csrftoken=")) {
      cookieValue = cookie.substring("csrftoken=".length);
    }
  }
  return cookieValue;
}
