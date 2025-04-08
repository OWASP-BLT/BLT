import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import path from "path";
import fs from "fs";
import { storage } from "./storage";
import { checkRepository } from "./compliance/checker";
import { generatePdfReport } from "./compliance/report";

export async function registerRoutes(app: Express): Promise<Server> {
  // API routes for OWASP compliance checker
  app.post("/api/compliance/check", async (req: Request, res: Response) => {
    try {
      const { url } = req.body;
      
      if (!url) {
        return res.status(400).json({ message: "Repository URL is required" });
      }

      // Validate URL format (should be a GitHub URL)
      const githubUrlPattern = /^https?:\/\/github\.com\/[a-zA-Z0-9\-_]+\/[a-zA-Z0-9\-_]+\/?$/;
      if (!githubUrlPattern.test(url)) {
        return res.status(400).json({ message: "Invalid GitHub repository URL" });
      }

      // Check repository compliance
      const report = await checkRepository(url);
      
      // Store report in memory storage
      const savedReport = await storage.saveComplianceReport(report);
      
      return res.status(200).json(savedReport);
    } catch (error) {
      console.error("Error checking compliance:", error);
      return res.status(500).json({ 
        message: error instanceof Error ? error.message : "An error occurred while checking compliance" 
      });
    }
  });

  app.post("/api/compliance/download", async (req: Request, res: Response) => {
    try {
      const { reportId } = req.body;
      
      if (!reportId) {
        return res.status(400).json({ message: "Report ID is required" });
      }

      // Retrieve report from storage
      const report = await storage.getComplianceReport(reportId);
      
      if (!report) {
        return res.status(404).json({ message: "Report not found" });
      }

      // Generate PDF report
      const pdfBuffer = await generatePdfReport(report);
      
      // Set response headers for PDF download
      res.setHeader("Content-Type", "application/pdf");
      res.setHeader("Content-Disposition", `attachment; filename="owasp-compliance-report-${report.repoName.replace(/\//g, "-")}.pdf"`);
      
      // Send PDF buffer
      return res.send(pdfBuffer);
    } catch (error) {
      console.error("Error generating report:", error);
      return res.status(500).json({ 
        message: error instanceof Error ? error.message : "An error occurred while generating the report" 
      });
    }
  });

  // Screenshots routes
  app.get("/screenshots/desktop", (req: Request, res: Response) => {
    const filePath = path.resolve("screenshots/desktop_view.html");
    res.sendFile(filePath);
  });

  app.get("/screenshots/mobile", (req: Request, res: Response) => {
    const filePath = path.resolve("screenshots/mobile_view.html");
    res.sendFile(filePath);
  });

  app.get("/screenshots/desktop_screenshot.png", (req: Request, res: Response) => {
    // Serve the high-resolution desktop screenshot
    const filePath = path.resolve("screenshots/desktop_screenshot.png");
    if (fs.existsSync(filePath)) {
      res.set('Content-Type', 'image/png');
      res.sendFile(filePath);
    } else {
      res.status(404).send('Screenshot not found');
    }
  });

  app.get("/screenshots/mobile_screenshot.png", (req: Request, res: Response) => {
    // Create a placeholder for the mobile screenshot if it doesn't exist
    const filePath = path.resolve("screenshots/mobile_screenshot.png");
    if (!fs.existsSync(filePath)) {
      // This is just a placeholder - we'll replace with real screenshots
      res.set('Content-Type', 'image/x-portable-pixmap');
      res.sendFile(path.resolve("screenshots/placeholder.ppm"));
    } else {
      res.sendFile(filePath);
    }
  });

  // Limitations document download
  app.get("/api/limitations/download", (req: Request, res: Response) => {
    try {
      // Path to the limitations file
      const filePath = path.resolve("server/compliance/limitations.md");
      
      if (!fs.existsSync(filePath)) {
        return res.status(404).json({ message: "Limitations document not found" });
      }
      
      // Read the file
      const fileContent = fs.readFileSync(filePath, 'utf8');
      
      // Set response headers for markdown file download
      res.setHeader("Content-Type", "text/markdown");
      res.setHeader("Content-Disposition", "attachment; filename=OWASP-Compliance-Checker-Limitations.md");
      
      // Send the file content
      return res.send(fileContent);
    } catch (error) {
      console.error("Error serving limitations document:", error);
      return res.status(500).json({ 
        message: error instanceof Error ? error.message : "An error occurred while serving the limitations document" 
      });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
