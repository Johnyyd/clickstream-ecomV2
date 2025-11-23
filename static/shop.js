// shop.js - simple storefront client
const Shop = (() => {
  const api = {
    async products(params = {}) {
      const query = new URLSearchParams(params).toString();
      const res = await fetch(`/api/products${query ? `?${query}` : ''}`);
      if (!res.ok) throw new Error('Failed to load products');
      return res.json();
    },
    async product(id) {
      const res = await fetch(`/api/product/${encodeURIComponent(id)}`);
      if (!res.ok) throw new Error('Product not found');
      return res.json();
    },
    async search(params) {
      let url = '/api/search';
      if (typeof params === 'string') {
        url += `?q=${encodeURIComponent(params)}`;
      } else if (params && typeof params === 'object') {
        const usp = new URLSearchParams();
        usp.set('q', params.q || '');
        if (params.limit != null) usp.set('limit', String(params.limit));
        if (params.offset != null) usp.set('offset', String(params.offset));
        if (params.sort) usp.set('sort', params.sort);
        if (params.min_price) usp.set('min_price', params.min_price);
        if (params.max_price) usp.set('max_price', params.max_price);
        if (params.tags) usp.set('tags', params.tags);
        url += `?${usp.toString()}`;
      }
      const res = await fetch(url);
      if (!res.ok) throw new Error('Search failed');
      return res.json();
    },
    async categories() {
      const res = await fetch('/api/categories');
      if (!res.ok) throw new Error('Failed to load categories');
      return res.json();
    },
    async recommendations({ limit = 12, offset = 0, sessionContext = null } = {}) {
      const token = getToken();
      if (!token) return { items: [] };

      if (sessionContext) {
        // Use POST to send session context
        const res = await fetch(`/api/recommendations?limit=${limit}&offset=${offset}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify(sessionContext)
        });
        if (!res.ok) return { items: [] };
        return res.json();
      }

      // Fallback to GET for backward compatibility
      const res = await fetch(`/api/recommendations?limit=${limit}&offset=${offset}`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!res.ok) return { items: [] };
      return res.json();
    }
  };

  // Cart in localStorage
  const CART_KEY = 'ecomv2_cart';
  const UID_KEY = 'ecomv2_user_id';
  const SID_KEY = 'ecomv2_session_id';

  // Simple in-memory UI state per page
  const state = {
    home: { limit: 8, offset: 0, sort: 'created_desc' },
    category: { limit: 8, offset: 0, sort: 'created_desc', category: '' },
    search: { limit: 8, offset: 0, query: '', filters: {} },
    reco: { limit: 4, offset: 0 },
    session: {
      viewedProducts: [],  // [{id, category, tags}, ...]
      maxViewed: 20  // Keep last 20 viewed products
    }
  };

  function getCart() {
    try {
      return JSON.parse(localStorage.getItem(CART_KEY)) || [];
    } catch {
      return [];
    }
  }

  function getToken() {
    try { return localStorage.getItem('token') || ''; } catch { return ''; }
  }

  async function syncServerCartFromLocal() {
    const token = getToken();
    if (!token) return;
    try {
      const items = getCart().map(x => ({ product_id: x.product_id, quantity: x.quantity || 1 }));
      await fetch('/api/cart', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ items })
      });
    } catch (e) { /* swallow */ }
  }

  function saveCart(items) {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
    updateCartCount();
    // Best-effort sync to server if logged in
    syncServerCartFromLocal();
  }
  function addToCart(item) {
    const items = getCart();
    const idx = items.findIndex(x => x.product_id === item.product_id);
    if (idx >= 0) {
      items[idx].quantity += item.quantity || 1;
    } else {
      items.push({ ...item, quantity: item.quantity || 1 });
    }
    saveCart(items);
    // Also call incremental API when logged in
    try {
      const token = getToken();
      if (token) {
        fetch('/api/cart/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ product_id: item.product_id, quantity: item.quantity || 1 })
        }).then(async () => {
          try {
            loadRecommendations();
            const resp = await fetch('/api/cart', { headers: { 'Authorization': 'Bearer ' + token } });
            if (resp.ok) {
              const data = await resp.json();
              const items2 = Array.isArray(data.items) ? data.items : [];
              localStorage.setItem(CART_KEY, JSON.stringify(items2.map(x => ({
                product_id: x.product_id,
                name: x.name,
                price: x.price,
                image_url: x.image_url,
                category: x.category,
                tags: x.tags || [],
                quantity: x.quantity || 1,
              }))));
              updateCartCount();
            }
          } catch { }
        }).catch(() => { });
      }
    } catch { }
  }
  function removeFromCart(product_id) {
    const items = getCart().filter(x => x.product_id !== product_id);
    saveCart(items);
    // Also call incremental API when logged in
    try {
      const token = getToken();
      if (token) {
        fetch('/api/cart/remove', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ product_id })
        }).then(async () => {
          try {
            const resp = await fetch('/api/cart', { headers: { 'Authorization': 'Bearer ' + token } });
            if (resp.ok) {
              const data = await resp.json();
              const items2 = Array.isArray(data.items) ? data.items : [];
              localStorage.setItem(CART_KEY, JSON.stringify(items2.map(x => ({
                product_id: x.product_id,
                name: x.name,
                price: x.price,
                image_url: x.image_url,
                category: x.category,
                tags: x.tags || [],
                quantity: x.quantity || 1,
              }))));
              updateCartCount();
            }
          } catch { }
        }).catch(() => { });
      }
    } catch { }
  }
  function setCartQuantity(product_id, qty) {
    const items = getCart();
    const idx = items.findIndex(x => x.product_id === product_id);
    if (idx >= 0) {
      items[idx].quantity = Math.max(1, Number(qty) || 1);
      saveCart(items);
    }
  }
  function updateCartCount() {
    const el = document.getElementById('cartCount');
    if (!el) return;
    const total = getCart().reduce((s, x) => s + x.quantity, 0);
    el.textContent = total > 0 ? `(${total})` : '';
  }

  function fmtPrice(n) {
    if (typeof n !== 'number') return n;
    return `$${n.toFixed(2)}`;
  }

  // --- Clickstream tracking ---
  function uuid() {
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
  }
  function getIds() {
    let uid = localStorage.getItem(UID_KEY) || '';
    if (!uid) { uid = uuid(); localStorage.setItem(UID_KEY, uid); }
    let sid = sessionStorage.getItem(SID_KEY) || '';
    if (!sid) { sid = `session_${uid}_${Date.now()}`; sessionStorage.setItem(SID_KEY, sid); }
    return { user_id: uid, session_id: sid };
  }
  async function track(page, event_type, properties = {}) {
    try {
      // Prefer SDK batching if present
      if (window.analytics && typeof window.analytics.track === 'function') {
        window.analytics.track(page, event_type, properties);
      }
      // Keep legacy single-event POST for backward compatibility
      const { user_id, session_id } = getIds();
      await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, session_id, page, event_type, properties, timestamp: Math.floor(Date.now() / 1000) })
      });
    } catch (e) { /* swallow */ }
  }

  function productCard(p) {
    const img = p.image_url || '/static/images/placeholder.svg';
    return `
  <div class="card">
    <a href="/p/${encodeURIComponent(p.slug || (p._id || p.product_id))}?id=${encodeURIComponent(p._id || p.product_id)}" class="card-image-wrapper">
      <img src="${img}" alt="${p.name}" onerror="this.onerror=null;this.src='/static/images/placeholder.svg'" />
    </a>
    <div class="card-body">
      <div class="card-category">${p.category}</div>
      <div class="card-title" title="${p.name}">${p.name}</div>
      <div class="card-price">${fmtPrice(p.price)}</div>
      <div class="card-actions">
        <button class="btn-add-cart" data-add="${encodeURIComponent(p._id || p.product_id)}">
          Add to Cart
        </button>
        <a class="btn-view" href="/p/${encodeURIComponent(p.slug || (p._id || p.product_id))}?id=${encodeURIComponent(p._id || p.product_id)}">
          View
        </a>
      </div>
    </div>
  </div>
`;
  }

  function bindAddButtons(container, items) {
    container.querySelectorAll('[data-add]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-add');
        const p = items.find(x => (x._id || x.product_id) === id);
        if (!p) return;
        addToCart({ product_id: (p._id || p.product_id), name: p.name, price: p.price, image_url: p.image_url, category: p.category, tags: p.tags || [], quantity: 1 });
        track('/cart', 'add_to_cart', { product_id: p._id || p.product_id, product_name: p.name, product_price: p.price });
      });
    });
    // Track view button clicks for session-based recommendations
    container.querySelectorAll('.btn-view').forEach(link => {
      link.addEventListener('click', () => {
        const href = link.getAttribute('href');
        const match = href.match(/[?&]id=([^&]+)/);
        if (match) {
          const id = decodeURIComponent(match[1]);
          const p = items.find(x => (x._id || x.product_id) === id);
          if (p) trackProductView(p);
        }
      });
    });
  }

  function renderSortControls(containerId, currentSort, onChange) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
  <label>Sort</label>
  <select id="sortSelect">
    <option value="created_desc">Newest</option>
    <option value="price_asc">Price: Low to High</option>
    <option value="price_desc">Price: High to Low</option>
    <option value="name_asc">Name: A â†’ Z</option>
    <option value="name_desc">Name: Z â†’ A</option>
  </select>`;
    const select = el.querySelector('#sortSelect');
    select.value = currentSort || 'created_desc';
    select.addEventListener('change', () => onChange(select.value));
  }

  // Session tracking for recommendations
  function trackProductView(product) {
    if (!product) return;

    const viewed = {
      id: product._id || product.product_id,
      category: product.category,
      tags: product.tags || []
    };

    // Add to front of array (most recent first)
    state.session.viewedProducts.unshift(viewed);

    // Keep only last N items
    if (state.session.viewedProducts.length > state.session.maxViewed) {
      state.session.viewedProducts = state.session.viewedProducts.slice(0, state.session.maxViewed);
    }
  }

  function buildSessionContext() {
    const cart = getCart();
    const cartIds = cart.map(item => item.product_id);

    // Extract categories and tags from viewed products and cart
    const categories = [];
    const tags = [];

    // From viewed products
    state.session.viewedProducts.forEach(p => {
      if (p.category) categories.push(p.category);
      if (p.tags && Array.isArray(p.tags)) tags.push(...p.tags);
    });

    // From cart items (they have more weight)
    cart.forEach(item => {
      if (item.category) {
        categories.push(item.category);
        categories.push(item.category); // Add twice for more weight
      }
      if (item.tags && Array.isArray(item.tags)) {
        tags.push(...item.tags);
      }
    });

    const viewedIds = state.session.viewedProducts.map(p => p.id);

    return {
      cart_product_ids: cartIds,
      viewed_product_ids: viewedIds,
      categories: categories,
      tags: tags
    };
  }

  // Map categories to appropriate icons
  function getCategoryIcon(category) {
    const categoryLower = category.toLowerCase();
    const iconMap = {
      'computer': 'fa-laptop',
      'computers': 'fa-laptop',
      'laptop': 'fa-laptop',
      'phone': 'fa-mobile-screen',
      'phones': 'fa-mobile-screen',
      'mobile': 'fa-mobile-screen',
      'accessories': 'fa-headphones',
      'accessory': 'fa-headphones',
      'camera': 'fa-camera',
      'cameras': 'fa-camera',
      'tablet': 'fa-tablet',
      'tablets': 'fa-tablet',
      'watch': 'fa-clock',
      'watches': 'fa-clock',
      'smartwatch': 'fa-clock',
      'audio': 'fa-volume-high',
      'speaker': 'fa-volume-high',
      'headphone': 'fa-headphones',
      'gaming': 'fa-gamepad',
      'monitor': 'fa-desktop',
      'keyboard': 'fa-keyboard',
      'mouse': 'fa-computer-mouse',
      'storage': 'fa-hard-drive',
      'network': 'fa-network-wired',
      'printer': 'fa-print'
    };

    for (const [key, icon] of Object.entries(iconMap)) {
      if (categoryLower.includes(key)) {
        return icon;
      }
    }
    // Default icon
    return 'fa-box';
  }

  async function loadCategories() {
    try {
      const grid = document.getElementById('categoryGrid');
      if (!grid) return;

      const { items } = await api.categories();
      if (!items || items.length === 0) return;

      grid.innerHTML = items.map(cat => {
        const icon = getCategoryIcon(cat.name);
        return `
        <a href="/category?category=${encodeURIComponent(cat.name)}" class="category-card">
          <i class="fa-solid ${icon} category-icon"></i>
          <span class="category-name">${cat.name}</span>
        </a>`;
      }).join('');
    } catch (e) {
      console.error('Error loading categories:', e);
    }
  }

  async function loadFeaturedProducts() {
    try {
      const grid = document.getElementById('productGrid');
      const info = document.getElementById('homeInfo');
      const controls = document.getElementById('homeSort');
      renderSortControls('homeSort', state.home.sort, (val) => { state.home.sort = val; state.home.offset = 0; loadFeaturedProducts(); });
      const { items, total, limit, offset } = await api.products({ limit: state.home.limit, offset: state.home.offset, sort: state.home.sort });
      if (state.home.offset === 0) grid.innerHTML = '';
      grid.insertAdjacentHTML('beforeend', items.map(productCard).join(''));
      bindAddButtons(grid, items);
      const moreBtn = document.getElementById('homeLoadMore');
      if (moreBtn) {
        const hasMore = offset + items.length < total;
        moreBtn.style.display = hasMore ? 'inline-block' : 'none';
        moreBtn.onclick = () => { state.home.offset += limit; loadFeaturedProducts(); };
      }
      if (info) info.textContent = `${offset + items.length}/${total}`;
      track('/home', 'pageview');
    } catch (e) {
      console.error(e);
    }
  }

  async function loadRecommendations() {
    try {
      const wrap = document.getElementById('recoWrap');
      const grid = document.getElementById('recoGrid');
      const moreBtn = document.getElementById('recoLoadMore');
      if (!wrap || !grid) return;

      // Reset if offset is 0 (new load or refresh)
      if (state.reco.offset === 0) {
        grid.innerHTML = '';
      }

      let items = [];
      let total = 0;

      try {
        // Build session context from current state
        const sessionContext = buildSessionContext();
        const res = await api.recommendations({
          limit: state.reco.limit,
          offset: state.reco.offset,
          sessionContext: sessionContext
        });
        items = res.items || [];
        total = res.total || 0;
      } catch (e) {
        console.error('Error loading recommendations:', e);
      }

      // Fallback: If no personal recommendations AND it's the first load, show latest products
      if (!items.length && state.reco.offset === 0) {
        try {
          const res = await api.products({ limit: 4, sort: 'created_desc' });
          items = res.items || [];
          // For fallback, we might not want pagination or we treat it differently. 
          // Let's assume fallback is just a static set for now or disable load more.
          if (moreBtn) moreBtn.style.display = 'none';
        } catch { }
      }

      if (!items.length && state.reco.offset === 0) {
        wrap.style.display = 'none';
        return;
      }

      wrap.style.display = 'block';
      grid.insertAdjacentHTML('beforeend', items.map(productCard).join(''));
      bindAddButtons(grid, items);

      if (moreBtn) {
        // Simple check: if we got fewer items than limit, we are probably at the end
        const hasMore = items.length === state.reco.limit;
        moreBtn.style.display = hasMore ? 'inline-block' : 'none';
        moreBtn.onclick = () => {
          state.reco.offset += state.reco.limit;
          loadRecommendations();
        };
      }

    } catch (e) { console.error(e); }
  }

  async function renderCategories(containerId = 'categoryFilters') {
    const el = document.getElementById(containerId);
    if (!el) return;
    try {
      const { items } = await api.categories();
      if (!items || !items.length) {
        el.innerHTML = '';
        return;
      }
      el.innerHTML = items.map(c => `<a class="btn" href="/category?category=${encodeURIComponent(c)}">${c}</a>`).join(' ');
    } catch (e) {
      console.error(e);
    }
  }

  function renderFilterControls(containerId, current, onApply) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
  <div class="search-bar" style="flex-wrap:wrap;gap:8px">
    <input id="minPrice" type="number" step="0.01" placeholder="Min price" style="max-width:140px"/>
    <input id="maxPrice" type="number" step="0.01" placeholder="Max price" style="max-width:140px"/>
    <input id="tags" placeholder="Tags (comma separated)" style="min-width:220px"/>
    <button id="applyFilters" class="btn">Apply</button>
  </div>`;
    el.querySelector('#minPrice').value = current.min_price || '';
    el.querySelector('#maxPrice').value = current.max_price || '';
    el.querySelector('#tags').value = current.tags || '';
    el.querySelector('#applyFilters').addEventListener('click', () => {
      onApply({
        min_price: el.querySelector('#minPrice').value,
        max_price: el.querySelector('#maxPrice').value,
        tags: el.querySelector('#tags').value,
      });
    });
  }

  async function loadCategoryFromQuery() {
    const usp = new URLSearchParams(location.search);
    const category = usp.get('category') || '';
    document.getElementById('categoryTitle').textContent = category ? `Category: ${category}` : 'All Products';
    const grid = document.getElementById('categoryGrid');
    const info = document.getElementById('categoryInfo');
    const sortBar = document.getElementById('categorySort');
    state.category.category = category;
    renderCategories();
    renderSortControls('categorySort', state.category.sort, (val) => { state.category.sort = val; state.category.offset = 0; loadCategoryFromQuery(); });
    renderFilterControls('categoryFilterBar', state.category, (filters) => {
      state.category = { ...state.category, ...filters };
      state.category.offset = 0;
      loadCategoryFromQuery();
    });
    const params = {
      category: state.category.category,
      limit: state.category.limit,
      offset: state.category.offset,
      sort: state.category.sort,
    };
    if (state.category.min_price) params.min_price = state.category.min_price;
    if (state.category.max_price) params.max_price = state.category.max_price;
    if (state.category.tags) params.tags = state.category.tags;

    const { items, total, limit, offset } = await api.products(params);
    if (state.category.offset === 0) grid.innerHTML = '';
    grid.insertAdjacentHTML('beforeend', items.map(productCard).join(''));
    bindAddButtons(grid, items);
    const moreBtn = document.getElementById('categoryLoadMore');
    if (moreBtn) {
      const hasMore = offset + items.length < total;
      moreBtn.style.display = hasMore ? 'inline-block' : 'none';
      moreBtn.onclick = () => { state.category.offset += limit; loadCategoryFromQuery(); };
    }
    if (info) info.textContent = `${offset + items.length}/${total}`;
    const pagePath = `/category?category=${encodeURIComponent(category)}`;
    track(pagePath, 'pageview', { category });
  }

  function initSearchPage() {
    const form = document.getElementById('searchForm');
    const results = document.getElementById('searchResults');
    const info = document.getElementById('searchInfo');
    renderSortControls('searchSort', state.search.sort, (val) => { state.search.sort = val; state.search.offset = 0; doSearch(); });
    renderFilterControls('searchFilterBar', state.search, (filters) => { state.search = { ...state.search, ...filters }; state.search.offset = 0; doSearch(); });
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      state.search.q = document.getElementById('q').value.trim();
      state.search.offset = 0;
      await doSearch(true);
    });

    async function doSearch(reset = false) {
      const params = {
        q: state.search.q || '',
        limit: state.search.limit,
        offset: state.search.offset,
        sort: state.search.sort,
      };
      if (state.search.min_price) params.min_price = state.search.min_price;
      if (state.search.max_price) params.max_price = state.search.max_price;
      if (state.search.tags) params.tags = state.search.tags;
      const { items, total, limit, offset } = await api.search(params);
      if (reset) results.innerHTML = '';
      results.insertAdjacentHTML('beforeend', items.map(productCard).join(''));
      bindAddButtons(results, items);
      const moreBtn = document.getElementById('searchLoadMore');
      if (moreBtn) {
        const hasMore = offset + items.length < total;
        moreBtn.style.display = hasMore ? 'inline-block' : 'none';
        moreBtn.onclick = async () => { state.search.offset += limit; await doSearch(); };
      }
      if (info) info.textContent = `${offset + items.length}/${total}`;
      track('/search', 'search', { search_term: params.q });
    }

  }

  async function loadProductFromQuery() {
    const usp = new URLSearchParams(location.search);
    // Support pretty URL /p/<slug>
    let p;
    if (location.pathname.startsWith('/p/')) {
      const slug = location.pathname.split('/p/')[1];
      try {
        const res = await fetch(`/api/product/slug/${encodeURIComponent(slug)}`);
        if (res.ok) {
          p = await res.json();
        }
      } catch { }
    } else if (location.pathname.startsWith('/product/')) {
      const pid = location.pathname.split('/product/')[1];
      if (pid) {
        try {
          const res = await fetch(`/api/product/${encodeURIComponent(pid)}`);
          if (res.ok) {
            p = await res.json();
          }
        } catch { }
      }
    }
    if (!p) {
      const id = usp.get('id');
      if (!id) return;
      p = await api.product(id);
    }
    const el = document.getElementById('productDetail');
    const img = p.image_url || '/static/images/placeholder.svg';
    el.innerHTML = `
  <nav class="breadcrumbs"><a href="/home">Home</a> <span>/</span> <a href="/category?category=${encodeURIComponent(p.category || '')}">${p.category || 'All'}</a> <span>/</span> <span>${p.name}</span></nav>
  <div class="product">
    <img src="${img}" alt="${p.name}" onerror="this.onerror=null;this.src='/static/images/placeholder.svg'" />
    <div class="product-info">
      <h1>${p.name}</h1>
      <div class="price">${fmtPrice(p.price)}</div>
      <div class="meta">Category: ${p.category}</div>
      <div class="tags">${(p.tags || []).map(t => `<span class="tag">${t}</span>`).join(' ')}</div>
      <div class="actions">
        <button id="addToCart" class="btn-primary">Add to Cart</button>
      </div>
    </div>
  </div>
  <h2>Related products</h2>
  <div id="relatedGrid" class="grid"></div>
`;
    // Track product pageview with product id in the page path
    try {
      const pagePath = `/product/${encodeURIComponent(p._id)}`;
      track(pagePath, 'pageview', { product_id: p._id, product_name: p.name, product_category: p.category, product_price: p.price });
      // Track for session-based recommendations
      trackProductView(p);
    } catch { }
    document.getElementById('addToCart').addEventListener('click', () => {
      addToCart({ product_id: p._id, name: p.name, price: p.price, image_url: p.image_url, category: p.category, tags: p.tags || [], quantity: 1 });
      track('/cart', 'add_to_cart', { product_id: p._id, product_name: p.name, product_price: p.price });
    });
    // load related
    try {
      if (p.category) {
        const { items } = await api.products({ category: p.category, limit: 8 });
        const grid = document.getElementById('relatedGrid');
        const filtered = items.filter(x => x._id !== p._id);
        grid.innerHTML = filtered.map(productCard).join('');
        bindAddButtons(grid, filtered);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function renderCartPage() {
    // Hydrate from server when logged in
    try {
      const token = getToken();
      if (token) {
        const resp = await fetch('/api/cart', { headers: { 'Authorization': 'Bearer ' + token } });
        if (resp.ok) {
          const data = await resp.json();
          const items = Array.isArray(data.items) ? data.items : [];
          // Normalize and persist to local for UI bindings
          localStorage.setItem(CART_KEY, JSON.stringify(items.map(x => ({
            product_id: x.product_id,
            name: x.name,
            price: x.price,
            image_url: x.image_url,
            quantity: x.quantity || 1,
          }))));
        }
      }
    } catch (e) { /* ignore */ }
    const items = getCart();
    const list = document.getElementById('cartItems');
    if (!items.length) {
      list.innerHTML = '<p>Your cart is empty.</p>';
      ['cartSubtotal', 'cartTax', 'cartShipping', 'cartTotal'].forEach(id => {
        const el = document.getElementById(id); if (el) el.textContent = '$0.00';
      });
      track('/cart', 'pageview', { items: 0 });
      return;
    }
    list.innerHTML = items.map(item => `
  <div class="cart-item">
    <img src="${item.image_url || '/static/images/placeholder.svg'}" alt="${item.name}">
    <div class="info">
      <div class="name">${item.name}</div>
      <div class="price">${fmtPrice(item.price)}</div>
    </div>
    <div>
      <input class="qty-input" type="number" min="1" step="1" value="${item.quantity}" data-qty="${item.product_id}" />
    </div>
    <button class="btn" data-remove="${item.product_id}">Remove</button>
  </div>
`).join('');
    list.querySelectorAll('[data-remove]').forEach(btn => {
      btn.addEventListener('click', () => {
        removeFromCart(btn.getAttribute('data-remove'));
        renderCartPage();
      });
    });
    list.querySelectorAll('[data-qty]').forEach(input => {
      input.addEventListener('change', () => {
        const id = input.getAttribute('data-qty');
        setCartQuantity(id, input.value);
        renderCartPage();
      });
    });
    const clearBtn = document.getElementById('clearCart');
    if (clearBtn) {
      clearBtn.onclick = async () => {
        localStorage.removeItem(CART_KEY);
        updateCartCount();
        track('/cart', 'clear_cart', { previous_items: items.length });
        try {
          const token = getToken();
          if (token) await fetch('/api/cart', { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
        } catch (e) { }
        renderCartPage();
      };
    }
    const subtotal = items.reduce((s, x) => s + x.price * x.quantity, 0);
    const tax = subtotal * 0.10;
    const shipping = subtotal > 0 ? 5.00 : 0.00;
    const total = subtotal + tax + shipping;
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = fmtPrice(v); };
    set('cartSubtotal', subtotal);
    set('cartTax', tax);
    set('cartShipping', shipping);
    set('cartTotal', total);
    track('/cart', 'pageview', { items: items.length, subtotal, tax, shipping, total_amount: total });
  }

  function initCheckoutPage() {
    const form = document.getElementById('checkoutForm');
    const status = document.getElementById('checkoutStatus');
    // Render order summary if elements exist
    const items = getCart();
    const subtotal = items.reduce((s, x) => s + x.price * x.quantity, 0);
    const tax = subtotal * 0.10;
    const shipping = subtotal > 0 ? 5.00 : 0.00;
    const total = subtotal + tax + shipping;
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = fmtPrice(v); };
    set('checkoutSubtotal', subtotal);
    set('checkoutTax', tax);
    set('checkoutShipping', shipping);
    set('checkoutTotal', total);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const items = getCart();
      if (!items.length) {
        status.textContent = 'Your cart is empty.';
        return;
      }
      // For demo purposes only â€“ accept checkout and clear cart
      const total = items.reduce((s, x) => s + x.price * x.quantity, 0);
      // 1) Send purchase event immediately to backend before redirect (do not rely only on batched SDK)
      try {
        const userObj = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null') || null; } catch { return null; } })();
        const user_id = (userObj && userObj.id) || localStorage.getItem('ecomv2_user_id') || '';
        const session_id = sessionStorage.getItem('ecomv2_session_id') || '';
        const payment_method = document.getElementById('payment')?.value || 'credit_card';
        const evt = {
          user_id,
          session_id,
          page: '/checkout',
          event_type: 'purchase',
          properties: { cart_items: items.length, total_amount: total, payment_method },
          timestamp: Math.floor(Date.now() / 1000)
        };
        await fetch('/api/ingest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(evt) });
        // also enqueue into SDK for consistency (non-blocking)
        try { if (window.analytics && typeof window.analytics.track === 'function') { window.analytics.track('/checkout', 'purchase', { cart_items: items.length, total_amount: total, payment_method }); } } catch { }
        // 2) Force-create order and clear server-side cart via backend endpoint (idempotent per cart)
        try {
          const token = getToken();
          if (token) {
            await fetch('/api/cart/checkout', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
              body: JSON.stringify({ session_id })
            });
          }
        } catch { }
      } catch { }
      // 3) Clear local cart and (again) ensure server cart is cleared
      localStorage.removeItem(CART_KEY);
      updateCartCount();
      // Best-effort: clear server-side cart if logged in (await to avoid being cancelled by redirect)
      try {
        const token = getToken();
        if (token) {
          await fetch('/api/cart', { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
        }
      } catch { }
      status.textContent = 'Order placed successfully!';
      setTimeout(() => { window.location.href = '/static/confirmation.html'; }, 600);
    });
  }

  function initNav() {
    updateCartCount();
    // track bare pageview if not already tracked in specific page loaders
    const path = location.pathname;
    if (['/home', '/category', '/search', '/product', '/cart', '/checkout'].indexOf(path) === -1) {
      track(path || '/', 'pageview');
    }
    // Active nav highlighting
    const navLinks = document.querySelectorAll('.site-header nav a');
    navLinks.forEach(a => {
      const href = a.getAttribute('href');
      if (!href) return;
      if (href === '/home' && (path === '/' || path.startsWith('/home'))) a.classList.add('active');
      else if (href.startsWith('/category') && path.startsWith('/category')) a.classList.add('active');
      else if (href.startsWith('/search') && path.startsWith('/search')) a.classList.add('active');
      else if (href.startsWith('/cart') && path.startsWith('/cart')) a.classList.add('active');
      else if (href.startsWith('/checkout') && path.startsWith('/checkout')) a.classList.add('active');
    });

    // Inject Logout button when logged in
    try {
      const token = localStorage.getItem('token');
      const nav = document.querySelector('.site-header nav');
      if (token && nav && !nav.querySelector('#logoutBtn')) {
        const sep = document.createTextNode(' ');
        const btn = document.createElement('a');
        btn.id = 'logoutBtn';
        btn.href = '#';
        btn.textContent = 'Logout';
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          try {
            track('/auth', 'logout');
          } catch { }
          try { localStorage.removeItem('token'); } catch { }
          try { sessionStorage.removeItem('ecomv2_session_id'); } catch { }
          setTimeout(() => { window.location.replace('/auth'); }, 50);
        });
        nav.appendChild(sep);
        nav.appendChild(btn);
      }
    } catch { }
  }

  return {
    initNav,
    loadCategories,
    loadFeaturedProducts,
    renderCategories,
    loadCategoryFromQuery,
    initSearchPage,
    loadProductFromQuery,
    renderCartPage,
    initCheckoutPage,
    loadRecommendations,
  };
})();
