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
    }
  };

  // Cart in localStorage
  const CART_KEY = 'ecomv2_cart';
  const CID_KEY = 'ecomv2_client_id';
  const SID_KEY = 'ecomv2_session_id';

  // Simple in-memory UI state per page
  const state = {
    home: { limit: 12, offset: 0, sort: 'created_desc' },
    category: { category: '', limit: 12, offset: 0, sort: 'created_desc', min_price: '', max_price: '', tags: '' },
    search: { q: '', limit: 12, offset: 0, sort: 'created_desc', min_price: '', max_price: '', tags: '' },
  };
  function getCart() {
    try {
      return JSON.parse(localStorage.getItem(CART_KEY)) || [];
    } catch {
      return [];
    }
  }
  function saveCart(items) {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
    updateCartCount();
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
  }
  function removeFromCart(product_id) {
    const items = getCart().filter(x => x.product_id !== product_id);
    saveCart(items);
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
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
  }
  function getIds() {
    let cid = localStorage.getItem(CID_KEY) || '';
    if (!cid) { cid = uuid(); localStorage.setItem(CID_KEY, cid); }
    let sid = sessionStorage.getItem(SID_KEY) || '';
    if (!sid) { sid = `session_${cid}_${Date.now()}`; sessionStorage.setItem(SID_KEY, sid); }
    return { client_id: cid, session_id: sid };
  }
  async function track(page, event_type, properties = {}) {
    try {
      // Prefer SDK batching if present
      if (window.analytics && typeof window.analytics.track === 'function') {
        window.analytics.track(page, event_type, properties);
      }
      // Keep legacy single-event POST for backward compatibility
      const { client_id, session_id } = getIds();
      await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id, session_id, page, event_type, properties, timestamp: Math.floor(Date.now()/1000) })
      });
    } catch (e) { /* swallow */ }
  }

  function productCard(p) {
    const img = p.image_url || '/static/images/placeholder.svg';
    return `
      <div class="card">
        <img src="${img}" alt="${p.name}" onerror="this.onerror=null;this.src='/static/images/placeholder.svg'" />
        <div class="card-body">
          <div class="card-title">${p.name}</div>
          <div class="card-meta">${p.category} • ${fmtPrice(p.price)}</div>
          <div class="card-actions">
            <a class="btn" href="/p/${encodeURIComponent(p.slug || p._id)}?id=${encodeURIComponent(p._id)}">View</a>
            <button class="btn-primary" data-add="${encodeURIComponent(p._id)}">Add to Cart</button>
          </div>
        </div>
      </div>
    `;
  }

  function bindAddButtons(container, items) {
    container.querySelectorAll('[data-add]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-add');
        const p = items.find(x => x._id === id);
        if (!p) return;
        addToCart({ product_id: p._id, name: p.name, price: p.price, image_url: p.image_url, quantity: 1 });
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
        <option value="name_asc">Name: A → Z</option>
        <option value="name_desc">Name: Z → A</option>
      </select>`;
    const select = el.querySelector('#sortSelect');
    select.value = currentSort || 'created_desc';
    select.addEventListener('change', () => onChange(select.value));
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
    track('/category', 'pageview', { category });
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
      } catch {}
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
    document.getElementById('addToCart').addEventListener('click', () => {
      addToCart({ product_id: p._id, name: p.name, price: p.price, image_url: p.image_url, quantity: 1 });
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

  function renderCartPage() {
    const items = getCart();
    const list = document.getElementById('cartItems');
    if (!items.length) {
      list.innerHTML = '<p>Your cart is empty.</p>';
      ['cartSubtotal','cartTax','cartShipping','cartTotal'].forEach(id => {
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
      clearBtn.onclick = () => {
        localStorage.removeItem(CART_KEY);
        updateCartCount();
        track('/cart', 'clear_cart', { previous_items: items.length });
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
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const items = getCart();
      if (!items.length) {
        status.textContent = 'Your cart is empty.';
        return;
      }
      // For demo purposes only – accept checkout and clear cart
      const total = items.reduce((s, x) => s + x.price * x.quantity, 0);
      track('/checkout', 'purchase', { cart_items: items.length, total_amount: total, payment_method: document.getElementById('payment').value || 'credit_card' });
      localStorage.removeItem(CART_KEY);
      updateCartCount();
      status.textContent = 'Order placed successfully!';
      setTimeout(() => { window.location.href = '/static/confirmation.html'; }, 600);
    });
  }

  function initNav() {
    updateCartCount();
    // track bare pageview if not already tracked in specific page loaders
    const path = location.pathname;
    if ([ '/home', '/category', '/search', '/product', '/cart', '/checkout' ].indexOf(path) === -1) {
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
  }

  return {
    initNav,
    loadFeaturedProducts,
    renderCategories,
    loadCategoryFromQuery,
    initSearchPage,
    loadProductFromQuery,
    renderCartPage,
    initCheckoutPage,
  };
})();
