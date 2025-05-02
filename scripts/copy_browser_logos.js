const fs = require('fs');
const path = require('path');

const commonBrowsers = [
    'chrome',
    'firefox',
    'safari',
    'edge',
    'opera',
    'brave',
    'comodo-dragon',
    'ie'
];

const sourceDir = path.join(__dirname, '..', 'node_modules', 'browser-logos');
const destBaseDir = path.join(__dirname, '..', 'website', 'static', 'img', 'browser-logos');

// Create default browser logo directory
const defaultDir = path.join(destBaseDir, 'default');
if (!fs.existsSync(defaultDir)) {
    fs.mkdirSync(defaultDir, { recursive: true });
}

// Copy a default browser logo
fs.copyFileSync(
    path.join(sourceDir, 'chrome', 'chrome_64x64.png'),
    path.join(defaultDir, 'browser_64x64.png')
);

// Copy logo for each browser
commonBrowsers.forEach(browser => {
    const browserSrcDir = path.join(sourceDir, browser);
    const browserDestDir = path.join(destBaseDir, browser);
    
    if (fs.existsSync(browserSrcDir)) {
        // Create browser directory if it doesn't exist
        if (!fs.existsSync(browserDestDir)) {
            fs.mkdirSync(browserDestDir, { recursive: true });
        }
        
        // Copy logo file
        const logoFile = `${browser}_64x64.png`;
        const srcPath = path.join(browserSrcDir, logoFile);
        const destPath = path.join(browserDestDir, logoFile);
        
        if (fs.existsSync(srcPath)) {
            fs.copyFileSync(srcPath, destPath);
            console.log(`Copied ${logoFile} for ${browser}`);
        } else {
            console.warn(`Logo file not found for ${browser}`);
        }
    } else {
        console.warn(`Source directory not found for ${browser}`);
    }
});