// github-integration/server.js



import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import { createHmac, timingSafeEqual } from 'crypto';
import fetch from 'node-fetch';

const app = express();

// Use raw body for signature verification
app.use(express.json({
  verify: (req, res, buf) => {
    req.rawBody = buf;
  }
}));

app.use((req, res, next) => {
  console.log(`[DEBUG] Incoming ${req.method} ${req.url}`);
  next();
});

// ===== ENV VARIABLES =====
const PORT = process.env.PORT || 3000;
const WEBHOOK_SECRET = process.env.GITHUB_WEBHOOK_SECRET || "mysecret";
const SIZZLE_API_KEY = process.env.SIZZLE_API_KEY || "yoursizzlekey";
const SIZZLE_API_URL = process.env.SIZZLE_API_URL || "https://your-sizzle-app.com/api/timers/start";

// ===== Verify GitHub signature =====
function verifySignature(req) {
  const signature = req.headers['x-hub-signature-256'];
  if (!signature) return false;

  const hmac = createHmac('sha256', WEBHOOK_SECRET);
  const digest = 'sha256=' + hmac.update(req.rawBody).digest('hex');
  try {
    return timingSafeEqual(Buffer.from(signature), Buffer.from(digest));
  } catch {
    return false;
  }
}

app.get('/', (req, res) => {
  res.send('Server running ');
});

// ===== Handle incoming webhook =====

app.post('/github/webhook', async (req, res) => {

  const event = req.headers['x-github-event'];
  console.log(` Received event: ${event}`);

  if (!verifySignature(req)) {
    console.log('Invalid signature');
    return res.status(401).send('Invalid signature');
  }

  const action = req.body.action;

  // ---- Handle issue labeled ----
  if (event === 'issues' && action === 'labeled') {
    const label = req.body.label.name;
    const issue = req.body.issue;
    const repo = req.body.repository.full_name;
    const user = req.body.sender.login;

    if (label === 'In Progress') {
      console.log(`Issue #${issue.number} in ${repo} is now In Progress`);

      try {
        // Call Sizzle API to start timer
       console.log(" Sending POST to Sizzle API:", SIZZLE_API_URL);
const resp = await fetch(SIZZLE_API_URL, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${SIZZLE_API_KEY}`,
  },
  body: JSON.stringify({
    issue_number: issue.number,
    issue_title: issue.title,
    repo: repo,
    actor: user,
  }),
});
console.log(" Sizzle API response:", resp.status);


        if (!resp.ok) {
          const text = await resp.text();
          console.error(" Failed to start Sizzle timer:", text);
          return res.status(500).send('Sizzle error');
        }

        console.log(' Timer started successfully in Sizzle');
        return res.status(200).send('OK');
      } catch (e) {
        console.error(' Error calling Sizzle:', e);
        return res.status(500).send('Error calling Sizzle');
      }
    }
  }

  // ---- Ignore other events ----
  return res.status(200).send('Ignored');
});

app.listen(PORT, () => console.log(` Webhook server running on port ${PORT}`));
