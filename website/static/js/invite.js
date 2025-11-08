/**
 * JavaScript functions for the invite organization page
 * Handles copy to clipboard functionality for referral links and email content
 */

function copyToClipboard(elementId) {
  const element = document.getElementById(elementId);
  if (!element) {
    console.warn("copyToClipboard: element not found", elementId);
    return;
  }
  const text = "value" in element ? element.value : element.textContent || "";

  // Check if clipboard API is available and we're in a secure context
  if (
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function" &&
    window.isSecureContext
  ) {
    navigator.clipboard
      .writeText(text)
      .then(function () {
        // Show success feedback
        const button = document.querySelector(
          `button[onclick="copyToClipboard('${elementId}')"]`
        );
        if (button) {
          const originalText = button.textContent;
          button.textContent = "Copied!";
          button.classList.add("bg-green-500", "text-white");
          button.classList.remove(
            "bg-gray-200",
            "hover:bg-gray-300",
            "text-gray-700"
          );

          setTimeout(function () {
            button.textContent = originalText;
            button.classList.remove("bg-green-500", "text-white");
            button.classList.add(
              "bg-gray-200",
              "hover:bg-gray-300",
              "text-gray-700"
            );
          }, 2000);
        }
      })
      .catch(function (err) {
        console.error("Failed to copy text: ", err);
        handleCopyFallback(
          element,
          "Copy failed. Text selected for manual copy."
        );
      });
  } else {
    // Provide specific error message based on the issue
    let errorMessage = "Unable to copy automatically. ";
    if (!window.isSecureContext) {
      errorMessage += "Clipboard access requires HTTPS. ";
    } else if (!navigator.clipboard) {
      errorMessage += "Clipboard API not supported in this browser. ";
    }
    errorMessage += "Text selected for manual copy.";

    handleCopyFallback(element, errorMessage);
  }
}

function handleCopyFallback(element, message) {
  alert(message);
  selectText(element);
}

function copyEmailContent() {
  const subject = document.getElementById("email-subject").textContent;
  const body = document.getElementById("email-body").textContent;
  const fullContent = `Subject: ${subject}\n\n${body}`;

  // Check if clipboard API is available and we're in a secure context
  if (
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function" &&
    window.isSecureContext
  ) {
    navigator.clipboard
      .writeText(fullContent)
      .then(function () {
        // Show success feedback
        const button = document.querySelector(
          'button[onclick="copyEmailContent()"]'
        );
        if (button) {
          const originalText = button.textContent;
          button.textContent = "Copied!";
          button.classList.add("bg-green-500");
          button.classList.remove("bg-[#e74c3c]", "hover:bg-red-600");

          setTimeout(function () {
            button.textContent = originalText;
            button.classList.remove("bg-green-500");
            button.classList.add("bg-[#e74c3c]", "hover:bg-red-600");
          }, 2000);
        }
      })
      .catch(function (err) {
        console.error("Failed to copy text: ", err);
        const bodyEl = document.getElementById("email-body");
        if (bodyEl) selectText(bodyEl);
        alert("Copy failed. Email content selected for manual copy.");
      });
  } else {
    // Provide specific error message based on the issue
    let errorMessage = "Unable to copy automatically. ";
    if (!window.isSecureContext) {
      errorMessage += "Clipboard access requires HTTPS. ";
    } else if (!navigator.clipboard) {
      errorMessage += "Clipboard API not supported in this browser. ";
    }
    errorMessage += "Email content selected for manual copy.";

    const bodyEl = document.getElementById("email-body");
    if (bodyEl) selectText(bodyEl);
    alert(errorMessage);
  }
}

function selectText(element) {
  if (!element) return;
  if (
    element instanceof HTMLInputElement ||
    element instanceof HTMLTextAreaElement
  ) {
    element.focus();
    element.select();
    return;
  }
  const range = document.createRange();
  range.selectNodeContents(element);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}
