// Lightweight analytics SDK with batching and retry
(function(){
  const QUEUE = [];
  const MAX_BATCH = 20;
  const FLUSH_INTERVAL_MS = 3000;
  const ENDPOINT = '/api/ingest-batch';

  function getIds(){
    try{
      const UID_KEY='ecomv2_user_id';
      const SID_KEY='ecomv2_session_id';

      // Nếu đã đăng nhập, ưu tiên dùng user.id từ backend để khớp với _id trong Mongo
      let uid = '';
      try{
        const userStr = localStorage.getItem('user');
        if (userStr) {
          const user = JSON.parse(userStr);
          if (user && user.id) {
            uid = String(user.id);
          }
        }
      }catch(e){ /* ignore parse errors, sẽ fallback UUID */ }

      // Nếu chưa có uid (chưa login), dùng UUID local như trước
      if(!uid){
        uid = localStorage.getItem(UID_KEY)||'';
        if(!uid){uid=crypto.randomUUID(); localStorage.setItem(UID_KEY,uid)}
      }

      // Generate session_id as a 24-hex string (ObjectId-like). Regenerate only when:
      // - no SID
      // - legacy SID (starts with "session_")
      let sid=sessionStorage.getItem(SID_KEY)||'';
      const legacy = (typeof sid === 'string' && sid.indexOf('session_') === 0);
      if(!sid || legacy){
        try{
          const bytes = crypto.getRandomValues(new Uint8Array(12));
          sid = Array.from(bytes).map(b => b.toString(16).padStart(2,'0')).join('');
        }catch(e){
          sid = Date.now().toString(16) + Math.floor(Math.random()*1e6).toString(16).padStart(6,'0');
        }
        sessionStorage.setItem(SID_KEY,sid);
      }
      return {user_id:uid, session_id:sid};
    }catch{ return {user_id:'', session_id:''}; }
  }

  async function flush(){
    if(QUEUE.length===0) return;
    const batch = QUEUE.splice(0, MAX_BATCH);
    try{
      await fetch(ENDPOINT, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ events: batch }) });
    }catch(e){
      // retry later by re-queueing at the front
      QUEUE.unshift(...batch);
    }
  }
  setInterval(flush, FLUSH_INTERVAL_MS);

  function track(page, event_type, properties){
    const ids = getIds();
    const evt = { page, event_type, properties: properties||{}, user_id: ids.user_id, session_id: ids.session_id, timestamp: Math.floor(Date.now()/1000) };
    QUEUE.push(evt);
    if(QUEUE.length>=MAX_BATCH) flush();
  }

  window.analytics = { track };
})();
