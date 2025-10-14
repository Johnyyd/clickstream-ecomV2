// Lightweight analytics SDK with batching and retry
(function(){
  const QUEUE = [];
  const MAX_BATCH = 20;
  const FLUSH_INTERVAL_MS = 3000;
  const ENDPOINT = '/api/ingest-batch';

  function getIds(){
    try{
      const CID_KEY='ecomv2_client_id';
      const SID_KEY='ecomv2_session_id';
      let cid=localStorage.getItem(CID_KEY)||'';
      if(!cid){cid=crypto.randomUUID(); localStorage.setItem(CID_KEY,cid)}
      let sid=sessionStorage.getItem(SID_KEY)||'';
      if(!sid){sid=`session_${cid}_${Date.now()}`; sessionStorage.setItem(SID_KEY,sid)}
      return {client_id:cid, session_id:sid};
    }catch{ return {client_id:'', session_id:''}; }
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
    const evt = { page, event_type, properties: properties||{}, client_id: ids.client_id, session_id: ids.session_id, timestamp: Math.floor(Date.now()/1000) };
    QUEUE.push(evt);
    if(QUEUE.length>=MAX_BATCH) flush();
  }

  window.analytics = { track };
})();
