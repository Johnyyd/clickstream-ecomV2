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

let token = null;

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
  // create 10 simple events
  for (let i=0;i<10;i++){
    const event = {
      client_id: "client-demo",
      page: i%3===0?"/home": (i%3===1?"/product":"/checkout"),
      event_type: "pageview",
      timestamp: Math.floor(Date.now()/1000)
    };
    await fetch('/api/ingest', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization': token},
      body: JSON.stringify(event)
    });
  }
  output.innerText = "10 events ingested";
}

analyzeBtn.onclick = async () => {
  if (!token) { output.innerText = "login first"; return; }
  
  // Hiển thị trạng thái đang phân tích
  output.innerText = "Analyzing data...";
  
  try {
    // Gọi API phân tích
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization': token},
      body: JSON.stringify({params: {limit: 1000}})
    });
    const result = await resp.json();
    
    if (result.error) {
      output.innerText = `Error: ${result.error}`;
      return;
    }
    
    // Nếu thành công, lấy kết quả phân tích
    if (result.analysis && result.analysis._id) {
      const analysisResp = await fetch(`/api/analyses/${result.analysis._id}`, {
        headers: {'Authorization': token}
      });
      const analysis = await analysisResp.json();
      
      // Tóm tắt nhanh (Python summary)
      const totalEvents = analysis?.spark_summary?.total_events ?? 0;
      const sessions = analysis?.spark_summary?.sessions ?? 0;
      const createdAt = analysis?.created_at ? new Date(analysis.created_at).toLocaleString() : '';
      const topPages = analysis?.spark_summary?.top_pages ?? [];
      const summary = {
        "Analysis Time": createdAt,
        "Total Events": totalEvents,
        "Total Sessions": sessions,
        "Top Pages (first 5)": topPages.slice(0,5)
      };
      summaryEl.textContent = JSON.stringify(summary, null, 2);

      // Hiển thị chi tiết Python analysis (detailed_metrics)
      pythonDetailsEl.textContent = JSON.stringify(analysis?.detailed_metrics ?? {}, null, 2);

      // Hiển thị LLM kết quả nếu có
      const llm = analysis?.openrouter_output || null;
      if (llm && llm.status === 'ok') {
        llmParsedEl.textContent = JSON.stringify(llm.parsed ?? {}, null, 2);
        llmRawEl.textContent = JSON.stringify(llm.raw ?? {}, null, 2);
      } else if (llm && llm.error) {
        llmParsedEl.textContent = JSON.stringify({ notice: 'LLM error', error: llm.error }, null, 2);
        llmRawEl.textContent = '';
      } else {
        llmParsedEl.textContent = JSON.stringify({ notice: 'No LLM output found for this user/analysis.' }, null, 2);
        llmRawEl.textContent = '';
      }

      output.innerText = "Analysis completed.";
      // Refresh recommendations panel based on the new analysis
      try { await loadRecommendations(); } catch(e) {}
    } else {
      output.innerText = JSON.stringify(result, null, 2);
    }
  } catch (error) {
    output.innerText = `Error: ${error.message}`;
  }
}

async function checkKey(){
  if (!token) { keyStatus.textContent = 'Login first'; return; }
  keyStatus.textContent = 'Checking key...';
  const resp = await fetch('/api/openrouter/key', { headers: {'Authorization': token} });
  const j = await resp.json();
  keyStatus.textContent = JSON.stringify(j, null, 2);
}

checkKeyBtn.onclick = async () => {
  try { await checkKey(); } catch (e) { keyStatus.textContent = String(e); }
};

saveKeyBtn.onclick = async () => {
  if (!token) { keyStatus.textContent = 'Login first'; return; }
  const k = openrouterKeyInput.value.trim();
  if (!k) { keyStatus.textContent = 'Please paste your OpenRouter API key'; return; }
  keyStatus.textContent = 'Saving key...';
  try {
    const resp = await fetch('/api/openrouter/key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': token },
      body: JSON.stringify({ api_key: k })
    });
    const j = await resp.json();
    if (resp.ok) {
      keyStatus.textContent = 'Saved. You can now run analysis to get LLM insights.';
      openrouterKeyInput.value = '';
      // Refresh status
      setTimeout(() => { checkKeyBtn.click(); }, 200);
    } else {
      keyStatus.textContent = JSON.stringify(j, null, 2);
    }
  } catch (e) {
    keyStatus.textContent = String(e);
  }
};
