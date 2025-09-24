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
    async search(q) {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error('Search failed');
      return res.json();
    },
  };

  // Cart in localStorage
  const CART_KEY = 'ecomv2_cart';
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

  function productCard(p) {
    const img = p.image_url || '/static/images/placeholder.svg';
    return `
      <div class="card">
        <img src="${img}" alt="${p.name}" />
        <div class="card-body">
          <div class="card-title">${p.name}</div>
          <div class="card-meta">${p.category} • ${fmtPrice(p.price)}</div>
          <div class="card-actions">
            <a class="btn" href="/product?id=${encodeURIComponent(p._id)}">View</a>
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

  async function loadFeaturedProducts() {
    try {
      const grid = document.getElementById('productGrid');
      const { items } = await api.products({ limit: 24 });
      grid.innerHTML = items.map(productCard).join('');
      bindAddButtons(grid, items);
    } catch (e) {
      console.error(e);
    }
  }

  async function loadCategoryFromQuery() {
    const usp = new URLSearchParams(location.search);
    const category = usp.get('category') || '';
    document.getElementById('categoryTitle').textContent = category ? `Category: ${category}` : 'All Products';
    const grid = document.getElementById('categoryGrid');
    const params = category ? { category } : {};
    const { items } = await api.products(params);
    grid.innerHTML = items.map(productCard).join('');
    bindAddButtons(grid, items);
  }

  function initSearchPage() {
    const form = document.getElementById('searchForm');
    const results = document.getElementById('searchResults');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = document.getElementById('q').value.trim();
      const { items } = await api.search(q);
      results.innerHTML = items.map(productCard).join('');
      bindAddButtons(results, items);
    });
  }

  async function loadProductFromQuery() {
    const usp = new URLSearchParams(location.search);
    const id = usp.get('id');
    if (!id) return;
    const p = await api.product(id);
    const el = document.getElementById('productDetail');
    const img = p.image_url || '/static/images/placeholder.svg';
    el.innerHTML = `
      <div class="product">
        <img src="${img}" alt="${p.name}" />
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
    `;
    document.getElementById('addToCart').addEventListener('click', () => {
      addToCart({ product_id: p._id, name: p.name, price: p.price, image_url: p.image_url, quantity: 1 });
    });
  }

  function renderCartPage() {
    const items = getCart();
    const list = document.getElementById('cartItems');
    if (!items.length) {
      list.innerHTML = '<p>Your cart is empty.</p>';
      document.getElementById('cartTotal').textContent = '$0.00';
      return;
    }
    list.innerHTML = items.map(item => `
      <div class="cart-item">
        <img src="${item.image_url || '/static/images/placeholder.svg'}" alt="${item.name}">
        <div class="info">
          <div class="name">${item.name}</div>
          <div class="price">${fmtPrice(item.price)} x ${item.quantity}</div>
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
    const total = items.reduce((s, x) => s + x.price * x.quantity, 0);
    document.getElementById('cartTotal').textContent = fmtPrice(total);
  }

  function initCheckoutPage() {
    const form = document.getElementById('checkoutForm');
    const status = document.getElementById('checkoutStatus');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const items = getCart();
      if (!items.length) {
        status.textContent = 'Your cart is empty.';
        return;
      }
      // For demo purposes only – accept checkout and clear cart
      localStorage.removeItem(CART_KEY);
      updateCartCount();
      status.textContent = 'Order placed successfully!';
    });
  }

  function initNav() {
    updateCartCount();
  }

  return {
    initNav,
    loadFeaturedProducts,
    loadCategoryFromQuery,
    initSearchPage,
    loadProductFromQuery,
    renderCartPage,
    initCheckoutPage,
  };
})();
