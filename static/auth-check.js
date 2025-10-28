/**
 * Auth Check Middleware
 * Kiểm tra authorization dựa trên role
 */

// Kiểm tra xem user đã đăng nhập chưa
function isLoggedIn() {
  return !!localStorage.getItem('token');
}

// Lấy thông tin user từ localStorage
function getCurrentUser() {
  try {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    return null;
  }
}

// Kiểm tra xem user có role admin không
function isAdmin() {
  const user = getCurrentUser();
  return user && user.role === 'admin';
}

// Redirect về trang login nếu chưa đăng nhập
function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = '/auth';
    return false;
  }
  return true;
}

// Redirect về home nếu không phải admin
function requireAdmin() {
  if (!requireAuth()) return false;
  
  if (!isAdmin()) {
    alert('Bạn không có quyền truy cập trang này. Chỉ dành cho admin.');
    window.location.href = '/home';
    return false;
  }
  return true;
}

// Logout function
function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  localStorage.removeItem('ecomv2_cart');
  sessionStorage.removeItem('ecomv2_session_id');
  window.location.href = '/auth';
}

// Export cho sử dụng trong các trang khác
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    isLoggedIn,
    getCurrentUser,
    isAdmin,
    requireAuth,
    requireAdmin,
    logout
  };
}
