const axios = require('axios');
const PROVISIONING_KEY = process.env.OPENROUTER_PROVISIONING_KEY;
const BASE = 'https://openrouter.ai/api/v1/keys';
const headers = {
  Authorization: `Bearer ${PROVISIONING_KEY}`,
  'Content-Type': 'application/json'
};

async function createRuntimeKey(name='runtime-js-auto', limit=null) {
  const payload = { name };
  if (limit) payload.limit = limit;
  const r = await axios.post(BASE, payload, { headers });
  return r.data; // contains 'key' and 'data'
}
