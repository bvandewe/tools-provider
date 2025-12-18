#!/usr/bin/env node

const nunjucks = require('nunjucks');
const fs = require('fs');
const path = require('path');

// Configure Nunjucks
const env = nunjucks.configure('src/templates', {
    autoescape: true,
    trimBlocks: true,
    lstripBlocks: true,
});

// Get app name from environment variable (with fallback)
const appName = process.env.AGENT_HOST_APP_NAME || 'Agent Host';

// Ensure build directory exists
const buildDir = path.join(__dirname, 'src', 'tmp_build');
if (!fs.existsSync(buildDir)) {
    fs.mkdirSync(buildDir, { recursive: true });
}

// Render the main chat template
const indexHtml = env.render('index.jinja', {
    title: `${appName} - AI Chat`,
    app_name: appName,
});
const indexOutputPath = path.join(buildDir, 'index.html');
fs.writeFileSync(indexOutputPath, indexHtml);
console.log('✓ Template rendered successfully to src/tmp_build/index.html');

// Render the admin template
const adminHtml = env.render('admin.jinja', {
    title: `${appName} - Admin`,
    app_name: appName,
});
const adminOutputPath = path.join(buildDir, 'admin.html');
fs.writeFileSync(adminOutputPath, adminHtml);
console.log('✓ Template rendered successfully to src/tmp_build/admin.html');
