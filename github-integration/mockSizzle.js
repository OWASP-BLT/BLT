// mockSizzle.js
import express from "express";

const app = express();
app.use(express.json());

// ✅ Mock endpoint for starting a timer
app.post("/api/timers/start", (req, res) => {
  console.log("🕒 Mock Sizzle API received request:");
  // For security, do not log the entire request body. Log only non-sensitive fields or a summary.
  if (req.body && typeof req.body === "object") {
    // Log only the keys of the request body, not the values
    console.log("Request body keys:", Object.keys(req.body));
  } else {
    console.log("Request body is empty or not an object.");
  }

  // Simulate a success response
  res.status(200).json({
    message: "✅ Timer started successfully (mock)",
    data: req.body,
  });
});

// ✅ Optional: A simple test route
app.get("/", (req, res) => {
  res.send("Mock Sizzle API is running 🚀");
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`🟢 Mock Sizzle API running on port ${PORT}`));
