const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = 'C:\\Users\\Admin\\.gemini\\antigravity\\brain\\cd7bf395-e162-4f13-a129-fb5899868b08';
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9222;

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function main() {
  console.log('[*] Spawning headless Chrome on port ' + PORT);
  const chromeProc = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--disable-gpu',
    '--no-sandbox',
    '--disable-extensions',
    '--window-size=1440,900',
    'about:blank'
  ]);

  let targetWsUrl = null;
  for (let i = 0; i < 20; i++) {
    await sleep(400);
    try {
      const tabs = await fetchJson(`http://127.0.0.1:${PORT}/json/list`);
      if (tabs && tabs.length > 0 && tabs[0].webSocketDebuggerUrl) {
        targetWsUrl = tabs[0].webSocketDebuggerUrl;
        break;
      }
    } catch (e) {}
  }

  if (!targetWsUrl) {
    console.error('[-] Could not get WebSocket URL from Chrome');
    chromeProc.kill();
    process.exit(1);
  }

  console.log('[+] Connected to Chrome CDP at: ' + targetWsUrl);
  const ws = new WebSocket(targetWsUrl);

  let msgId = 1;
  const pendingRequests = new Map();
  const consoleLogs = [];
  const consoleErrors = [];

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.id && pendingRequests.has(data.id)) {
      const resolver = pendingRequests.get(data.id);
      pendingRequests.delete(data.id);
      resolver(data.result);
    }

    if (data.method === 'Runtime.consoleAPICalled') {
      const type = data.params.type;
      const text = data.params.args.map(a => a.value || JSON.stringify(a)).join(' ');
      consoleLogs.push(`[${type}] ${text}`);
      if (type === 'error') {
        consoleErrors.push(text);
      }
    }

    if (data.method === 'Runtime.exceptionThrown') {
      const desc = data.params.exceptionDetails?.exception?.description || data.params.exceptionDetails?.text;
      consoleErrors.push(`[EXCEPTION] ${desc}`);
    }
  };

  await new Promise(r => ws.onopen = r);

  function sendCmd(method, params = {}) {
    return new Promise((resolve) => {
      const id = msgId++;
      pendingRequests.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async function evaluate(expression) {
    const res = await sendCmd('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    return res?.result?.value;
  }

  async function setViewport(width, height) {
    await sendCmd('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 2,
      mobile: width < 768
    });
    await sendCmd('Emulation.setVisibleSize', { width, height });
    await sleep(200);
  }

  async function captureScreenshot(filename) {
    const res = await sendCmd('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(res.data, 'base64');
    
    // Save to workspace
    fs.writeFileSync(filename, buffer);
    console.log(`[+] Saved screenshot: ${filename} (${buffer.length} bytes)`);

    // Copy to artifact directory
    const artifactPath = path.join(ARTIFACT_DIR, filename);
    fs.writeFileSync(artifactPath, buffer);
    console.log(`[+] Copied to artifact: ${artifactPath}`);
  }

  // Enable CDP domains
  await sendCmd('Page.enable');
  await sendCmd('Runtime.enable');
  await sendCmd('Console.enable');

  console.log('[*] Navigating to http://127.0.0.1:3000...');
  await sendCmd('Page.navigate', { url: 'http://127.0.0.1:3000' });

  // Wait for page load and agent readiness
  for (let i = 0; i < 30; i++) {
    await sleep(400);
    const ready = await evaluate('window.agentReady === true');
    if (ready) {
      console.log('[+] Agent reported ready on frontend!');
      break;
    }
  }

  await sleep(600);

  // 1. Desktop Dashboard (1440x900)
  console.log('[*] Capturing 1. Desktop Dashboard (1440px)...');
  await setViewport(1440, 900);
  await evaluate('window.switchView("dashboard")');
  await sleep(400);
  await captureScreenshot('desktop_redesign_1440.png');

  // 2. Club Detail Modal (Interactive Inspection)
  console.log('[*] Capturing 2. Club Detail Modal (CodeCraft)...');
  await evaluate('window.openClubDetail("CodeCraft")');
  await sleep(500);
  await captureScreenshot('club_detail_modal.png');
  await evaluate('window.closeClubDetail()');
  await sleep(300);

  // 3. Ask Agent View (with conversation feed)
  console.log('[*] Capturing 3. Ask Agent Chat View...');
  await evaluate('window.switchView("chat")');
  await sleep(400);
  await captureScreenshot('ask_agent_view.png');

  // 4. Event Timeline View (with interactive search filter)
  console.log('[*] Capturing 4. Event Timeline View (Search: Workshop)...');
  await evaluate('window.switchView("events")');
  await sleep(300);
  await evaluate(`
    const inp = document.getElementById("timeline-search-input");
    if (inp) {
      inp.value = "Workshop";
      inp.dispatchEvent(new Event("input", { bubbles: true }));
    }
  `);
  await sleep(400);
  await captureScreenshot('event_timeline_view.png');

  // Reset search
  await evaluate(`
    const inp = document.getElementById("timeline-search-input");
    if (inp) {
      inp.value = "";
      inp.dispatchEvent(new Event("input", { bubbles: true }));
    }
  `);

  // 5. Full Institutional Report View
  console.log('[*] Capturing 5. Full Institutional Report View...');
  await evaluate('window.switchView("report")');
  await sleep(500);
  await captureScreenshot('full_report_view.png');

  // 6. Approvals / Human Review View
  console.log('[*] Capturing 6. Approvals View (Queue & Actions)...');
  await evaluate('window.switchView("approvals")');
  await sleep(500);
  await captureScreenshot('approvals_view.png');

  // 7. Laptop Dashboard (1280x800)
  console.log('[*] Capturing 7. Laptop Dashboard (1280px)...');
  await evaluate('window.switchView("dashboard")');
  await setViewport(1280, 800);
  await sleep(400);
  await captureScreenshot('laptop_redesign_1280.png');

  // 8. Tablet Dashboard (768x1024)
  console.log('[*] Capturing 8. Tablet Dashboard (768px)...');
  await setViewport(768, 1024);
  await sleep(400);
  await captureScreenshot('tablet_redesign_768.png');

  // 9. Mobile Dashboard (390x844)
  console.log('[*] Capturing 9. Mobile Dashboard (390px)...');
  await setViewport(390, 844);
  await sleep(400);
  await captureScreenshot('mobile_redesign_390.png');

  // Also update standard files for artifact viewer
  fs.copyFileSync('desktop_redesign_1440.png', path.join(ARTIFACT_DIR, 'desktop_redesign.png'));
  fs.copyFileSync('tablet_redesign_768.png', path.join(ARTIFACT_DIR, 'tablet_redesign.png'));
  fs.copyFileSync('mobile_redesign_390.png', path.join(ARTIFACT_DIR, 'mobile_redesign.png'));

  console.log('\n=========================================');
  console.log('BROWSER CONSOLE ERROR AUDIT:');
  console.log(`Total Console Messages: ${consoleLogs.length}`);
  console.log(`Total Console Errors/Exceptions: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.error('Errors encountered:', consoleErrors);
  } else {
    console.log('[PASS] ZERO JavaScript runtime errors or uncaught exceptions detected.');
  }
  console.log('=========================================\n');

  ws.close();
  chromeProc.kill();
  console.log('[+] Finished all captures successfully.');
}

main().catch(err => {
  console.error('Fatal execution error:', err);
  process.exit(1);
});
