import { ComplianceReport } from "@shared/schema";
import PDFDocument from "pdfkit";

export async function generatePdfReport(report: ComplianceReport): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    try {
      // Create a new PDF document
      const doc = new PDFDocument({ 
        margin: 50,
        size: 'A4'
      });
      
      // Set up a buffer to store the PDF
      const buffers: Buffer[] = [];
      doc.on('data', buffers.push.bind(buffers));
      doc.on('end', () => {
        const pdfBuffer = Buffer.concat(buffers);
        resolve(pdfBuffer);
      });

      // Add document title
      doc.fontSize(24)
        .font('Helvetica-Bold')
        .text('OWASP Compliance Report', { align: 'center' })
        .moveDown(0.5);

      // Add horizontal line
      doc.moveTo(50, doc.y)
        .lineTo(doc.page.width - 50, doc.y)
        .stroke()
        .moveDown(0.5);

      // Add repository information
      doc.fontSize(12)
        .font('Helvetica')
        .text(`Repository: ${report.repoName}`)
        .text(`URL: ${report.repoUrl}`)
        .text(`Generated: ${new Date(report.createdAt).toLocaleString()}`)
        .moveDown(1);

      // Overall Score
      doc.fontSize(18)
        .font('Helvetica-Bold')
        .text(`Overall Score: ${Math.round(report.overallScore)}/100`)
        .fontSize(14)
        .font('Helvetica')
        .text(getScoreRating(report.overallScore))
        .moveDown(1);

      // Category Scores
      doc.fontSize(16)
        .font('Helvetica-Bold')
        .text('Category Scores:')
        .moveDown(0.5);
      
      report.categories.forEach(category => {
        doc.fontSize(12)
          .font('Helvetica')
          .text(`• ${category.name}: ${category.score}/${category.maxPoints}`);
      });
      doc.moveDown(1);

      // Key Recommendations
      if (report.recommendations.length > 0) {
        doc.fontSize(16)
          .font('Helvetica-Bold')
          .text('Key Recommendations:')
          .moveDown(0.5);
        
        report.recommendations.forEach(rec => {
          doc.fontSize(12)
            .font('Helvetica-Bold')
            .text(`• ${rec.category}:`, { continued: true })
            .font('Helvetica')
            .text(` ${rec.text}`);
        });
        doc.moveDown(1);
      }

      // Detailed Analysis
      doc.fontSize(16)
        .font('Helvetica-Bold')
        .text('Detailed Analysis:')
        .moveDown(0.5);

      // Loop through each category for detailed analysis
      report.categories.forEach(category => {
        // Add category header
        doc.fontSize(14)
          .font('Helvetica-Bold')
          .text(`${category.name} (${category.score}/${category.maxPoints})`)
          .moveDown(0.5);
        
        // List each checkpoint
        category.checkpoints.forEach(checkpoint => {
          const symbol = checkpoint.passed ? '✓' : '✗';
          const symbolColor = checkpoint.passed ? 'green' : 'red';
          
          doc.fontSize(12);
          
          // Add checkpoint status and description
          doc.font('Helvetica-Bold')
            .fillColor(symbolColor)
            .text(symbol, { continued: true })
            .fillColor('black')
            .font('Helvetica')
            .text(` ${checkpoint.description}`);
          
          // Add recommendation if checkpoint failed
          if (!checkpoint.passed && checkpoint.recommendation) {
            doc.fontSize(10)
              .text(`   Recommendation: ${checkpoint.recommendation}`, { indent: 10 });
          }
        });
        
        doc.moveDown(1);
      });

      // Add Limitations Disclaimer
      doc.addPage();
      doc.fontSize(16)
        .font('Helvetica-Bold')
        .text('Important Disclaimer:')
        .moveDown(0.5);
      
      doc.fontSize(10)
        .font('Helvetica')
        .text('This compliance assessment is an automated evaluation based on available repository data and should not be considered a comprehensive security audit. The following limitations apply:')
        .moveDown(0.5);
      
      const limitations = [
        'Automated Assessment: This tool performs checks based on repository data visible via the GitHub API. It cannot detect all security vulnerabilities.',
        'Technical Limitations: The assessment examines repository structure and patterns, but cannot execute code to verify runtime security.',
        'Context Specificity: Different projects have different security requirements based on their use case and environment.',
        'Point-in-Time: This report represents a snapshot and may not reflect recent repository changes.',
        'Evolving Standards: Security best practices evolve over time.'
      ];
      
      limitations.forEach(limitation => {
        doc.text(`• ${limitation}`);
      });
      
      doc.moveDown(0.5)
        .text('For critical applications, supplement this report with manual code reviews, penetration testing, and security audits by qualified personnel.')
        .moveDown(0.5)
        .text('For a complete explanation of assessment limitations, please download the limitations document available on the compliance checker website.');

      // Finalize the PDF
      doc.end();
    } catch (error) {
      reject(error);
    }
  });
}

function getScoreRating(score: number): string {
  if (score >= 90) return "Rating: Excellent - This project follows OWASP best practices.";
  if (score >= 80) return "Rating: Good - The project has solid security practices with some room for improvement.";
  if (score >= 70) return "Rating: Satisfactory - The project meets basic security requirements but needs improvements.";
  if (score >= 50) return "Rating: Needs Improvement - The project has significant security gaps that should be addressed.";
  return "Rating: Poor - The project requires immediate security improvements.";
}
