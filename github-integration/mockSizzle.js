// mockSizzle.js
import express from "express";

const app = express();
app.use(express.json());

// ✅ Mock endpoint for starting a timer
app.post("/api/timers/start", (req, res) => {
  console.log("🕒 Mock Sizzle API received request:");
  console.log(req.body);

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

const PORT = 5000;
app.listen(PORT, () => console.log(`🟢 Mock Sizzle API running on port ${PORT}`));
