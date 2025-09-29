// Import displayAnalysisResults from the analysisDisplay module
import { displayAnalysisResults } from './analysisDisplay.js';

// DOM Elements
const loginBtn = document.getElementById('loginBtn');
const simulateBtn = document.getElementById('simulateBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const output = document.getElementById('output');
const summaryEl = document.getElementById('summary');
const pythonDetailsEl = document.getElementById('pythonDetails');
const llmParsedEl = document.getElementById('llmParsed');
const llmRawEl = document.getElementById('llmRaw');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const checkKeyBtn = document.getElementById('checkKeyBtn');
const openrouterKeyInput = document.getElementById('openrouterKey');
const keyStatus = document.getElementById('keyStatus');
const recsEl = document.getElementById('recs');
const useSparkToggle = document.getElementById('useSparkToggle');
const analysisModeText = document.getElementById('analysisModeText');
const analysisModeBadge = document.getElementById('analysisModeBadge');

// State
let token = null;
let useSpark = true;

loginBtn.onclick = async () => {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const resp = await fetch('/api/login', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({username, password})
  });
  const j = await resp.json();
  if (j.token) {
    token = j.token;
    output.innerText = "Logged in!";
    document.getElementById('controls').style.display = 'block';
    // After login, check current key
    try { await checkKey(); } catch(e) {}
    // Also load latest recommendations if any
    try { await loadRecommendations(); } catch(e) {}
  } else {
    output.innerText = JSON.stringify(j);
  }
};

simulateBtn.onclick = async () => {
  if (!token) { output.innerText = "login first"; return; }
  output.innerText = "Simulating 10 events...";
  
  try {
    // create 10 simple events
    for (let i = 0; i < 10; i++) {
      const event = {
        client_id: "client-demo",
        page: i % 3 === 0 ? "/home" : (i % 3 === 1 ? "/product" : "/checkout"),
        event_type: "pageview",
        timestamp: Math.floor(Date.now() / 1000)
      };
      
      await fetch('/api/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token
        },
        body: JSON.stringify(event)
      });
    }
    
    output.innerText = "10 events ingested successfully";
  } catch (error) {
    console.error('Error simulating events:', error);
    output.innerText = `Error: ${error.message}`;
  }
};

// Toggle between Spark and Python analysis
if (useSparkToggle) {
  useSparkToggle.addEventListener('change', (e) => {
    useSpark = e.target.checked;
    e.target.setAttribute('aria-checked', useSpark.toString());
    updateAnalysisModeUI();
    
    // Save preference to localStorage
    localStorage.setItem('useSpark', useSpark.toString());
    
    // Notify screen readers of the change
    const mode = useSpark ? 'Spark' : 'Python';
    const statusMessage = `Analysis mode changed to ${mode}`;
    const statusEl = document.createElement('div');
    statusEl.setAttribute('role', 'status');
    statusEl.textContent = statusMessage;
    document.body.appendChild(statusEl);
    
    // Remove the status message after it's been announced
    setTimeout(() => {
      document.body.removeChild(statusEl);
    }, 1000);
  });
}

// Update UI based on analysis mode
function updateAnalysisModeUI() {
  const mode = useSpark ? 'Spark' : 'Python';
  if (analysisModeText) {
    analysisModeText.textContent = `${mode} Analysis`;
    analysisModeText.setAttribute('aria-label', `Current analysis engine: ${mode}`);
    
    // Update the tooltip based on the mode
    analysisModeText.title = useSpark 
      ? 'Using Apache Spark for large-scale data processing' 
      : 'Using Python for small to medium datasets';
  }
  
  if (analysisModeBadge) {
    analysisModeBadge.textContent = mode;
    analysisModeBadge.className = `badge ${mode.toLowerCase()}`;
    analysisModeBadge.setAttribute('aria-hidden', 'true');
    
    // Add tooltip to the badge
    analysisModeBadge.title = useSpark 
      ? 'Click to switch to Python analysis' 
      : 'Click to switch to Spark analysis';
  }
  
  // Update the analyze button text and tooltip
  if (analyzeBtn) {
    analyzeBtn.textContent = `Run ${mode} Analysis`;
    analyzeBtn.title = `Run analysis using ${mode} engine`;
  }
}

// Load analysis mode preference from localStorage
function loadPreferences() {
  const savedUseSpark = localStorage.getItem('useSpark');
  if (savedUseSpark !== null) {
    useSpark = savedUseSpark === 'true';
    if (useSparkToggle) useSparkToggle.checked = useSpark;
    updateAnalysisModeUI();
  }
}

// Check the current analysis mode from the server
async function checkAnalysisMode() {
  if (!token) return;
  
  try {
    const resp = await fetch('/api/analysis/mode', {
      headers: { 'Authorization': token }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      const serverUseSpark = data.use_spark;
      
      // Update UI if it doesn't match the server
      if (serverUseSpark !== useSpark) {
        useSpark = serverUseSpark;
        if (useSparkToggle) useSparkToggle.checked = useSpark;
        updateAnalysisModeUI();
        output.innerText = `Server is using ${useSpark ? 'Spark' : 'Python'} analysis`;
      }
    }
  } catch (e) {
    console.error('Failed to check analysis mode:', e);
  }
}

// displayAnalysisResults is now imported from analysisDisplay.js

// Check OpenRouter API key status
async function checkKey() {
  if (!token) return;
  
  try {
    const resp = await fetch('/api/openrouter/key', {
      headers: { 'Authorization': token }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      if (data.exists && data.masked_key) {
        keyStatus.innerHTML = `✅ API Key is set: <code>${data.masked_key}</code>`;
        keyStatus.className = 'key-status success';
        return true;
      } else {
        keyStatus.textContent = '❌ No API Key found';
        keyStatus.className = 'key-status error';
        return false;
      }
    } else {
      const error = await resp.json().catch(() => ({}));
      keyStatus.textContent = `❌ Error: ${error.error || 'Failed to check key'}`;
      keyStatus.className = 'key-status error';
      return false;
    }
  } catch (e) {
    console.error('Error checking key:', e);
    keyStatus.textContent = `❌ Error: ${e.message}`;
    keyStatus.className = 'key-status error';
    return false;
  }
}

// Save OpenRouter API key
async function saveKey() {
  if (!token) {
    output.innerText = 'Please login first';
    return false;
  }
  
  const key = openrouterKeyInput.value.trim();
  if (!key) {
    keyStatus.textContent = '❌ Please enter an API key';
    keyStatus.className = 'key-status error';
    return false;
  }
  
  try {
    const resp = await fetch('/api/openrouter/key', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token
      },
      body: JSON.stringify({ key })
    });
    
    if (resp.ok) {
      const data = await resp.json();
      keyStatus.textContent = '✅ API Key saved successfully';
      keyStatus.className = 'key-status success';
      openrouterKeyInput.value = ''; // Clear the input field
      return true;
    } else {
      const error = await resp.json().catch(() => ({}));
      keyStatus.textContent = `❌ Error: ${error.error || 'Failed to save key'}`;
      keyStatus.className = 'key-status error';
      return false;
    }
  } catch (e) {
    console.error('Error saving key:', e);
    keyStatus.textContent = `❌ Error: ${e.message}`;
    keyStatus.className = 'key-status error';
    return false;
  }
}

// Load product recommendations
async function loadRecommendations() {
  if (!token) return;
  
  try {
    const resp = await fetch('/api/recommendations', {
      headers: { 'Authorization': token }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      if (data.recommendations && data.recommendations.length > 0) {
        recsEl.innerHTML = '<h3>Recommended for You</h3>';
        const ul = document.createElement('ul');
        
        data.recommendations.forEach(rec => {
          const li = document.createElement('li');
          li.innerHTML = `
            <a href="/product/${rec.product_id}">
              <img src="${rec.image_url || '/static/images/placeholder.jpg'}" alt="${rec.name}">
              <h4>${rec.name}</h4>
              <p>$${rec.price?.toFixed(2) || 'N/A'}</p>
            </a>
          `;
          ul.appendChild(li);
        });
        
        recsEl.appendChild(ul);
      } else {
        recsEl.innerHTML = '<p>No recommendations available. Generate some by analyzing your data!</p>';
      }
    }
  } catch (e) {
    console.error('Error loading recommendations:', e);
    recsEl.innerHTML = '<p>Error loading recommendations. Please try again later.</p>';
  }
}

// Event listeners for key management
if (saveKeyBtn) {
  saveKeyBtn.addEventListener('click', saveKey);
}

if (checkKeyBtn) {
  checkKeyBtn.addEventListener('click', checkKey);
}

// Initialize
loadPreferences();

// Set initial ARIA attributes
if (useSparkToggle) {
  useSparkToggle.setAttribute('aria-checked', useSpark.toString());
  useSparkToggle.setAttribute('role', 'switch');
  useSparkToggle.setAttribute('aria-labelledby', 'analysisModeLabel');
}

analyzeBtn.onclick = async () => {
  if (!token) { output.innerText = "login first"; return; }
  output.innerText = `Running analysis with ${useSpark ? 'Spark' : 'Python'}...`;
  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token
      },
      body: JSON.stringify({
        params: { 
          limit: 1000,
          use_spark: useSpark
        }
      })
    });
    
    if (!resp.ok) {
      const error = await resp.json().catch(() => ({}));
      throw new Error(error.error || 'Failed to run analysis');
    }
    
    const j = await resp.json();
    if (j.error) {
      output.innerText = `Error: ${j.error}`;
      return;
    }
    
    // Get the full analysis using the returned ID
    const analysisResp = await fetch(`/api/analyses/${j.analysis._id}`, {
      headers: { 'Authorization': token }
    });
    
    if (!analysisResp.ok) {
      throw new Error('Failed to fetch analysis details');
    }
    
    const analysis = await analysisResp.json();
    
    // Display the results in the results container
    const resultsContainer = document.getElementById('results');
    displayAnalysisResults(analysis, resultsContainer);
    
    // Check the current analysis mode from the server
    checkAnalysisMode();
    
  } catch (e) {
    output.innerText = `Error: ${e.message}`;
    console.error('Analysis error:', e);
  }
};
