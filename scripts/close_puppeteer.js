const puppeteer = require('puppeteer');

async function closePuppeteerInstance(wsEndpoint) {
  try {
    const browser = await puppeteer.connect({ browserWSEndpoint: wsEndpoint });
    await browser.close();
    console.log('Puppeteer instance closed successfully.');
  } catch (error) {
    console.error('Error closing Puppeteer instance:', error);
  }
}

// Get command line arguments
const args = process.argv.slice(2);

if (args.length !== 1) {
  console.error('Usage: node closePuppeteerInstance.js <wsEndpoint>');
  process.exit(1);
}

const wsEndpoint = args[0];
closePuppeteerInstance(wsEndpoint);