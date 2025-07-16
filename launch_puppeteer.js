const puppeteer = require('puppeteer');

async function getBrowserWSEndpoint() {
  try {
    const browser = await puppeteer.launch({  
          headless: true,
          defaultViewport: null,
          executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
      });
    const browserWSEndpoint = browser.wsEndpoint();
    return browserWSEndpoint;
  } catch (error) {
    console.error('Error launching Puppeteer:', error);
    return null;
  }
}

getBrowserWSEndpoint().then((endpoint) => {
  console.log(endpoint);
});

