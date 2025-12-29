// Vercel serverless function - handles all /api/* requests
const app = require('../backend/src/app');

// Export for Vercel serverless
module.exports = app;

// Also export as default for ES module compatibility
module.exports.default = app;
