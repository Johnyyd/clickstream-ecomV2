const loginBtn = document.getElementById('loginBtn');
const simulateBtn = document.getElementById('simulateBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const output = document.getElementById('output');

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
      
      // Hiển thị kết quả chi tiết
      const details = {
        "Total Events": analysis.spark_summary?.total_events || 0,
        "Total Sessions": analysis.spark_summary?.sessions || 0,
        "Top Pages": analysis.spark_summary?.top_pages || [],
        "Home to Product Conversion": analysis.spark_summary?.funnel_home_to_product || 0,
        "Analysis Time": new Date(analysis.created_at).toLocaleString()
      };
      
      output.innerText = JSON.stringify(details, null, 2);
    } else {
      output.innerText = JSON.stringify(result, null, 2);
    }
  } catch (error) {
    output.innerText = `Error: ${error.message}`;
  }
}
