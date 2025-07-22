import React, { useState, useEffect, createContext, useContext, useCallback } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Context for user authentication
const AuthContext = createContext();
const CartContext = createContext();

// Custom hooks
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};

// Generate session ID
const getSessionId = () => {
  let sessionId = localStorage.getItem('session_id');
  if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    localStorage.setItem('session_id', sessionId);
  }
  return sessionId;
};

// Auth Provider
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const register = async (email, password, fullName) => {
    try {
      await axios.post(`${API}/auth/register`, {
        email,
        password,
        full_name: fullName
      });
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Registration failed' };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Cart Provider
const CartProvider = ({ children }) => {
  const [cartItems, setCartItems] = useState([]);
  const [cartCount, setCartCount] = useState(0);
  const [cartTotal, setCartTotal] = useState(0);
  const sessionId = getSessionId();

  const fetchCart = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/cart/${sessionId}`);
      setCartItems(response.data.items);
      setCartCount(response.data.items_count);
      setCartTotal(response.data.total_amount);
    } catch (error) {
      console.error('Failed to fetch cart:', error);
    }
  }, [sessionId]);

  const addToCart = async (productId, quantity = 1) => {
    try {
      await axios.post(`${API}/cart/add?product_id=${productId}&quantity=${quantity}&session_id=${sessionId}`);
      await fetchCart();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Failed to add to cart' };
    }
  };

  const updateCart = async (itemId, quantity) => {
    try {
      await axios.put(`${API}/cart/update/${itemId}?quantity=${quantity}`);
      await fetchCart();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Failed to update cart' };
    }
  };

  const removeFromCart = async (itemId) => {
    try {
      await axios.delete(`${API}/cart/remove/${itemId}`);
      await fetchCart();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Failed to remove from cart' };
    }
  };

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  return (
    <CartContext.Provider value={{
      cartItems,
      cartCount,
      cartTotal,
      addToCart,
      updateCart,
      removeFromCart,
      fetchCart,
      sessionId
    }}>
      {children}
    </CartContext.Provider>
  );
};

// Components
const Navigation = ({ currentPage, setCurrentPage }) => {
  const { user, logout } = useAuth();
  const { cartCount } = useCart();

  return (
    <nav className="bg-white shadow-lg border-b-2 border-blue-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 
              className="text-2xl font-bold text-gray-800 cursor-pointer hover:text-blue-600 transition-colors"
              onClick={() => setCurrentPage('home')}
            >
              🛒 ShopEase
            </h1>
          </div>
          
          <div className="hidden md:flex items-center space-x-8">
            <button
              onClick={() => setCurrentPage('home')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'home' ? 'text-blue-600 bg-blue-50' : 'text-gray-700 hover:text-blue-600'
              }`}
            >
              Home
            </button>
            <button
              onClick={() => setCurrentPage('products')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'products' ? 'text-blue-600 bg-blue-50' : 'text-gray-700 hover:text-blue-600'
              }`}
            >
              Products
            </button>
            <button
              onClick={() => setCurrentPage('cart')}
              className={`relative px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'cart' ? 'text-blue-600 bg-blue-50' : 'text-gray-700 hover:text-blue-600'
              }`}
            >
              Cart
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                  {cartCount}
                </span>
              )}
            </button>
          </div>
          
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <span className="text-sm text-gray-700">Welcome, {user.full_name}</span>
                <button
                  onClick={() => setCurrentPage('orders')}
                  className="text-sm text-gray-700 hover:text-blue-600"
                >
                  Orders
                </button>
                <button
                  onClick={logout}
                  className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setCurrentPage('login')}
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Login
                </button>
                <button
                  onClick={() => setCurrentPage('register')}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  Sign Up
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

const HomePage = ({ setCurrentPage }) => {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const { addToCart } = useCart();

  useEffect(() => {
    fetchFeaturedProducts();
  }, []);

  const fetchFeaturedProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`);
      setFeaturedProducts(response.data.slice(0, 6));
    } catch (error) {
      console.error('Failed to fetch products:', error);
    }
  };

  const handleAddToCart = async (productId) => {
    const result = await addToCart(productId);
    if (result.success) {
      alert('Product added to cart!');
    } else {
      alert(result.error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-5xl md:text-6xl font-bold mb-6">
              Welcome to <span className="text-yellow-300">ShopEase</span>
            </h1>
            <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto">
              Discover amazing products at unbeatable prices. From cutting-edge electronics to stylish clothing and essential home items.
            </p>
            <button
              onClick={() => setCurrentPage('products')}
              className="bg-yellow-400 text-gray-900 hover:bg-yellow-300 px-8 py-4 rounded-lg text-lg font-semibold transition-all transform hover:scale-105 shadow-lg"
            >
              Shop Now 🚀
            </button>
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">Shop by Category</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow cursor-pointer transform hover:scale-105"
                 onClick={() => setCurrentPage('products', 'electronics')}>
              <img 
                src="https://images.unsplash.com/photo-1498049794561-7780e7231661?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxlbGVjdHJvbmljc3xlbnwwfHx8fDE3NTMyMDU4MTd8MA&ixlib=rb-4.1.0&q=85" 
                alt="Electronics" 
                className="w-full h-48 object-cover"
              />
              <div className="p-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Electronics</h3>
                <p className="text-gray-600">Latest gadgets and tech accessories</p>
              </div>
            </div>
            
            <div className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow cursor-pointer transform hover:scale-105"
                 onClick={() => setCurrentPage('products', 'clothing')}>
              <img 
                src="https://images.unsplash.com/photo-1441984904996-e0b6ba687e04?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwxfHxjbG90aGluZ3xlbnwwfHx8fDE3NTMyMDU4MjN8MA&ixlib=rb-4.1.0&q=85" 
                alt="Clothing" 
                className="w-full h-48 object-cover"
              />
              <div className="p-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Clothing</h3>
                <p className="text-gray-600">Trendy fashion for every occasion</p>
              </div>
            </div>
            
            <div className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow cursor-pointer transform hover:scale-105"
                 onClick={() => setCurrentPage('products', 'home_essentials')}>
              <img 
                src="https://images.unsplash.com/photo-1691057185806-ea8b5b9a4506?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwxfHxob21lJTIwZXNzZW50aWFsc3xlbnwwfHx8fDE3NTMyMDU4MzJ8MA&ixlib=rb-4.1.0&q=85" 
                alt="Home Essentials" 
                className="w-full h-48 object-cover"
              />
              <div className="p-6">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Home Essentials</h3>
                <p className="text-gray-600">Everything you need for your home</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">Featured Products</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {featuredProducts.map((product) => (
              <div key={product.id} className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-all transform hover:scale-105">
                <img 
                  src={product.image_url} 
                  alt={product.name}
                  className="w-full h-48 object-cover"
                />
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{product.name}</h3>
                  <p className="text-gray-600 text-sm mb-4 line-clamp-2">{product.description}</p>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-2xl font-bold text-blue-600">${product.price}</span>
                    <div className="flex items-center">
                      <span className="text-yellow-400 mr-1">⭐</span>
                      <span className="text-sm text-gray-600">{product.rating} ({product.reviews_count})</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleAddToCart(product.id)}
                    className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-md font-medium transition-colors"
                  >
                    Add to Cart
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

const ProductsPage = ({ category = null }) => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(category);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const { addToCart } = useCart();

  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, [selectedCategory, searchTerm]);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.append('category', selectedCategory);
      if (searchTerm) params.append('search', searchTerm);
      
      const response = await axios.get(`${API}/products?${params}`);
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to fetch products:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data.categories);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const handleAddToCart = async (productId) => {
    const result = await addToCart(productId);
    if (result.success) {
      alert('Product added to cart!');
    } else {
      alert(result.error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Products</h1>
          
          {/* Search and Filters */}
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Search products..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <select
                value={selectedCategory || ''}
                onChange={(e) => setSelectedCategory(e.target.value || null)}
                className="px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="text-gray-500">Loading products...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {products.map((product) => (
              <div key={product.id} className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
                <img 
                  src={product.image_url} 
                  alt={product.name}
                  className="w-full h-48 object-cover"
                />
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">{product.name}</h3>
                  <p className="text-gray-600 text-sm mb-3 line-clamp-2">{product.description}</p>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-lg font-bold text-blue-600">${product.price}</span>
                    <div className="flex items-center">
                      <span className="text-yellow-400 mr-1">⭐</span>
                      <span className="text-sm text-gray-600">{product.rating}</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mb-3">
                    Stock: {product.stock} | Reviews: {product.reviews_count}
                  </div>
                  <button
                    onClick={() => handleAddToCart(product.id)}
                    disabled={product.stock === 0}
                    className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
                      product.stock > 0
                        ? 'bg-blue-500 hover:bg-blue-600 text-white'
                        : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    }`}
                  >
                    {product.stock > 0 ? 'Add to Cart' : 'Out of Stock'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && products.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-500">No products found.</div>
          </div>
        )}
      </div>
    </div>
  );
};

const CartPage = () => {
  const { cartItems, cartTotal, updateCart, removeFromCart, sessionId } = useCart();
  const [loading, setLoading] = useState(false);

  const handleUpdateQuantity = async (itemId, quantity) => {
    const result = await updateCart(itemId, quantity);
    if (!result.success) {
      alert(result.error);
    }
  };

  const handleRemoveItem = async (itemId) => {
    const result = await removeFromCart(itemId);
    if (!result.success) {
      alert(result.error);
    }
  };

  const handleCheckout = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/checkout/session?session_id=${sessionId}`);
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'Checkout failed');
      setLoading(false);
    }
  };

  if (cartItems.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Your Cart is Empty</h2>
            <p className="text-gray-600">Add some products to get started!</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Shopping Cart</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            {cartItems.map((item) => (
              <div key={item.id} className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center space-x-4">
                  <img 
                    src={item.product.image_url} 
                    alt={item.product.name}
                    className="w-20 h-20 object-cover rounded-md"
                  />
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{item.product.name}</h3>
                    <p className="text-gray-600">${item.product.price}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleUpdateQuantity(item.id, item.quantity - 1)}
                      className="w-8 h-8 flex items-center justify-center bg-gray-200 rounded-full hover:bg-gray-300"
                    >
                      -
                    </button>
                    <span className="w-12 text-center">{item.quantity}</span>
                    <button
                      onClick={() => handleUpdateQuantity(item.id, item.quantity + 1)}
                      className="w-8 h-8 flex items-center justify-center bg-gray-200 rounded-full hover:bg-gray-300"
                    >
                      +
                    </button>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">${item.item_total.toFixed(2)}</p>
                    <button
                      onClick={() => handleRemoveItem(item.id)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6 h-fit">
            <h3 className="text-lg font-semibold mb-4">Order Summary</h3>
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span>Subtotal:</span>
                <span>${cartTotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Shipping:</span>
                <span>Free</span>
              </div>
              <div className="border-t pt-2 flex justify-between font-semibold">
                <span>Total:</span>
                <span>${cartTotal.toFixed(2)}</span>
              </div>
            </div>
            <button
              onClick={handleCheckout}
              disabled={loading}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 px-4 rounded-md font-medium transition-colors disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Proceed to Checkout'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const AuthPage = ({ isLogin, setCurrentPage }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = isLogin 
      ? await login(email, password)
      : await register(email, password, fullName);

    if (result.success) {
      if (isLogin) {
        setCurrentPage('home');
      } else {
        alert('Registration successful! Please login.');
        setCurrentPage('login');
      }
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {isLogin ? 'Sign in to your account' : 'Create your account'}
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            {!isLogin && (
              <div>
                <label htmlFor="fullName" className="sr-only">Full Name</label>
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Full name"
                />
              </div>
            )}
            
            <div>
              <label htmlFor="email" className="sr-only">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Email address"
              />
            </div>
            
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Processing...' : (isLogin ? 'Sign in' : 'Sign up')}
            </button>
          </div>
          
          <div className="text-center">
            <button
              type="button"
              onClick={() => setCurrentPage(isLogin ? 'register' : 'login')}
              className="text-blue-600 hover:text-blue-500"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const OrdersPage = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const { sessionId } = useCart();

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const params = user ? {} : { session_id: sessionId };
      const response = await axios.get(`${API}/orders`, { params });
      setOrders(response.data);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">Loading orders...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Your Orders</h1>
        
        {orders.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600">No orders found.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {orders.map((order) => (
              <div key={order.id} className="bg-white rounded-lg shadow-md p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">Order #{order.id.slice(-8)}</h3>
                    <p className="text-gray-600">
                      {new Date(order.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold">${order.total_amount.toFixed(2)}</p>
                    <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${
                      order.payment_status === 'paid' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {order.payment_status}
                    </span>
                  </div>
                </div>
                
                <div className="space-y-2">
                  {order.items.map((item, index) => (
                    <div key={index} className="flex justify-between items-center text-sm">
                      <span>{item.name} x {item.quantity}</span>
                      <span>${item.item_total.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const SuccessPage = () => {
  const [status, setStatus] = useState('checking');
  const [message, setMessage] = useState('Verifying payment...');

  useEffect(() => {
    checkPaymentStatus();
  }, []);

  const checkPaymentStatus = async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
      setStatus('error');
      setMessage('Invalid session');
      return;
    }

    try {
      // Poll payment status
      let attempts = 0;
      const maxAttempts = 10;
      
      while (attempts < maxAttempts) {
        const response = await axios.get(`${API}/checkout/status/${sessionId}`);
        
        if (response.data.payment_status === 'paid') {
          setStatus('success');
          setMessage('Payment successful! Your order has been confirmed.');
          break;
        } else if (response.data.status === 'expired') {
          setStatus('error');
          setMessage('Payment session expired.');
          break;
        }
        
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
      
      if (attempts >= maxAttempts) {
        setStatus('error');
        setMessage('Payment verification timed out. Please check your orders.');
      }
    } catch (error) {
      setStatus('error');
      setMessage('Error verifying payment. Please check your orders.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8 text-center">
        {status === 'checking' && (
          <div>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold mb-2">Processing Payment</h2>
            <p className="text-gray-600">{message}</p>
          </div>
        )}
        
        {status === 'success' && (
          <div>
            <div className="text-green-500 text-5xl mb-4">✓</div>
            <h2 className="text-xl font-semibold mb-2 text-green-700">Payment Successful!</h2>
            <p className="text-gray-600 mb-6">{message}</p>
            <button
              onClick={() => window.location.href = '/'}
              className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-md"
            >
              Continue Shopping
            </button>
          </div>
        )}
        
        {status === 'error' && (
          <div>
            <div className="text-red-500 text-5xl mb-4">✗</div>
            <h2 className="text-xl font-semibold mb-2 text-red-700">Payment Failed</h2>
            <p className="text-gray-600 mb-6">{message}</p>
            <button
              onClick={() => window.location.href = '/cart'}
              className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-md"
            >
              Back to Cart
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [pageParams, setPageParams] = useState(null);

  const setPage = (page, params = null) => {
    setCurrentPage(page);
    setPageParams(params);
  };

  // Check if we're on success page
  useEffect(() => {
    const path = window.location.pathname;
    const search = window.location.search;
    
    if (path === '/success' || search.includes('session_id')) {
      setCurrentPage('success');
    }
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage setCurrentPage={setPage} />;
      case 'products':
        return <ProductsPage category={pageParams} />;
      case 'cart':
        return <CartPage />;
      case 'login':
        return <AuthPage isLogin={true} setCurrentPage={setCurrentPage} />;
      case 'register':
        return <AuthPage isLogin={false} setCurrentPage={setCurrentPage} />;
      case 'orders':
        return <OrdersPage />;
      case 'success':
        return <SuccessPage />;
      default:
        return <HomePage setCurrentPage={setPage} />;
    }
  };

  return (
    <AuthProvider>
      <CartProvider>
        <div className="App">
          {currentPage !== 'success' && (
            <Navigation currentPage={currentPage} setCurrentPage={setCurrentPage} />
          )}
          {renderPage()}
        </div>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;