#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for E-Commerce System
Tests all critical APIs including authentication, products, cart, payments, orders, and reviews.
"""

import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
BASE_URL = "https://a74befa2-b03e-40e2-88c2-2427e7f44441.preview.emergentagent.com/api"
SESSION_ID = f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"

class ECommerceAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session_id = SESSION_ID
        self.auth_token = None
        self.user_data = None
        self.test_results = []
        self.product_ids = []
        self.cart_item_ids = []
        
    def log_result(self, test_name: str, success: bool, message: str, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def make_request(self, method: str, endpoint: str, data: dict = None, headers: dict = None) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        url = f"{self.base_url}{endpoint}"
        default_headers = {"Content-Type": "application/json"}
        
        if headers:
            default_headers.update(headers)
            
        if self.auth_token and "Authorization" not in default_headers:
            default_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=default_headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=default_headers, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=default_headers, timeout=30)
            else:
                return False, {"error": "Unsupported method"}, 0
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text}
            
            return response.status_code < 400, response_data, response.status_code
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}, 0
    
    def test_product_catalog_apis(self):
        """Test Product Catalog APIs"""
        print("\n🛍️  Testing Product Catalog APIs...")
        
        # Test 1: Get all products
        success, data, status = self.make_request("GET", "/products")
        if success and isinstance(data, list) and len(data) > 0:
            self.product_ids = [product["id"] for product in data[:3]]  # Store first 3 product IDs
            self.log_result("GET /api/products", True, f"Retrieved {len(data)} products successfully")
        else:
            self.log_result("GET /api/products", False, "Failed to retrieve products", str(data))
        
        # Test 2: Get products by category
        success, data, status = self.make_request("GET", "/products?category=electronics")
        if success and isinstance(data, list):
            electronics_count = len(data)
            self.log_result("GET /api/products (category filter)", True, f"Retrieved {electronics_count} electronics products")
        else:
            self.log_result("GET /api/products (category filter)", False, "Failed to filter by category", str(data))
        
        # Test 3: Search products
        success, data, status = self.make_request("GET", "/products?search=wireless")
        if success and isinstance(data, list):
            search_count = len(data)
            self.log_result("GET /api/products (search)", True, f"Search returned {search_count} products")
        else:
            self.log_result("GET /api/products (search)", False, "Failed to search products", str(data))
        
        # Test 4: Get single product
        if self.product_ids:
            product_id = self.product_ids[0]
            success, data, status = self.make_request("GET", f"/products/{product_id}")
            if success and data.get("id") == product_id:
                self.log_result("GET /api/products/{id}", True, f"Retrieved product details for {data.get('name', 'Unknown')}")
            else:
                self.log_result("GET /api/products/{id}", False, "Failed to get product details", str(data))
        
        # Test 5: Get categories
        success, data, status = self.make_request("GET", "/categories")
        if success and "categories" in data and len(data["categories"]) > 0:
            categories = data["categories"]
            self.log_result("GET /api/categories", True, f"Retrieved {len(categories)} categories: {', '.join(categories)}")
        else:
            self.log_result("GET /api/categories", False, "Failed to get categories", str(data))
    
    def test_user_authentication_apis(self):
        """Test User Authentication APIs"""
        print("\n🔐 Testing User Authentication APIs...")
        
        # Test 1: User Registration
        register_data = {
            "email": f"john.doe.{int(time.time())}@example.com",
            "full_name": "John Doe",
            "password": "SecurePassword123!"
        }
        
        success, data, status = self.make_request("POST", "/auth/register", register_data)
        if success and data.get("email") == register_data["email"]:
            self.user_data = data
            self.log_result("POST /api/auth/register", True, f"User registered successfully: {data.get('full_name')}")
        else:
            self.log_result("POST /api/auth/register", False, "Failed to register user", str(data))
            return
        
        # Test 2: User Login
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        
        success, data, status = self.make_request("POST", "/auth/login", login_data)
        if success and "access_token" in data:
            self.auth_token = data["access_token"]
            self.log_result("POST /api/auth/login", True, f"Login successful, token received")
        else:
            self.log_result("POST /api/auth/login", False, "Failed to login", str(data))
            return
        
        # Test 3: Get Current User (Protected Route)
        success, data, status = self.make_request("GET", "/auth/me")
        if success and data.get("email") == register_data["email"]:
            self.log_result("GET /api/auth/me", True, f"Retrieved current user: {data.get('full_name')}")
        else:
            self.log_result("GET /api/auth/me", False, "Failed to get current user", str(data))
        
        # Test 4: Test invalid credentials
        invalid_login = {
            "email": register_data["email"],
            "password": "WrongPassword"
        }
        success, data, status = self.make_request("POST", "/auth/login", invalid_login)
        if not success and status == 401:
            self.log_result("POST /api/auth/login (invalid)", True, "Correctly rejected invalid credentials")
        else:
            self.log_result("POST /api/auth/login (invalid)", False, "Should have rejected invalid credentials", str(data))
    
    def test_shopping_cart_apis(self):
        """Test Shopping Cart APIs"""
        print("\n🛒 Testing Shopping Cart APIs...")
        
        if not self.product_ids:
            self.log_result("Cart Tests", False, "No products available for cart testing")
            return
        
        # Test 1: Add items to cart
        product_id = self.product_ids[0]
        add_data = {
            "product_id": product_id,
            "quantity": 2,
            "session_id": self.session_id
        }
        
        success, data, status = self.make_request("POST", f"/cart/add?product_id={product_id}&quantity=2&session_id={self.session_id}")
        if success:
            self.log_result("POST /api/cart/add", True, "Item added to cart successfully")
        else:
            self.log_result("POST /api/cart/add", False, "Failed to add item to cart", str(data))
        
        # Add second item
        if len(self.product_ids) > 1:
            product_id2 = self.product_ids[1]
            success, data, status = self.make_request("POST", f"/cart/add?product_id={product_id2}&quantity=1&session_id={self.session_id}")
            if success:
                self.log_result("POST /api/cart/add (second item)", True, "Second item added to cart")
            else:
                self.log_result("POST /api/cart/add (second item)", False, "Failed to add second item", str(data))
        
        # Test 2: Get cart contents
        success, data, status = self.make_request("GET", f"/cart/{self.session_id}")
        if success and "items" in data and len(data["items"]) > 0:
            cart_items = data["items"]
            self.cart_item_ids = [item["id"] for item in cart_items]
            total_amount = data.get("total_amount", 0)
            items_count = data.get("items_count", 0)
            self.log_result("GET /api/cart/{session_id}", True, f"Retrieved cart with {items_count} items, total: ${total_amount:.2f}")
        else:
            self.log_result("GET /api/cart/{session_id}", False, "Failed to get cart contents", str(data))
        
        # Test 3: Update cart item quantity
        if self.cart_item_ids:
            item_id = self.cart_item_ids[0]
            success, data, status = self.make_request("PUT", f"/cart/update/{item_id}?quantity=3")
            if success:
                self.log_result("PUT /api/cart/update/{item_id}", True, "Cart item quantity updated successfully")
            else:
                self.log_result("PUT /api/cart/update/{item_id}", False, "Failed to update cart item", str(data))
        
        # Test 4: Remove cart item
        if len(self.cart_item_ids) > 1:
            item_id = self.cart_item_ids[1]
            success, data, status = self.make_request("DELETE", f"/cart/remove/{item_id}")
            if success:
                self.log_result("DELETE /api/cart/remove/{item_id}", True, "Cart item removed successfully")
            else:
                self.log_result("DELETE /api/cart/remove/{item_id}", False, "Failed to remove cart item", str(data))
        
        # Test 5: Verify cart after modifications
        success, data, status = self.make_request("GET", f"/cart/{self.session_id}")
        if success and "items" in data:
            items_count = data.get("items_count", 0)
            self.log_result("GET /api/cart (after modifications)", True, f"Cart now has {items_count} items")
        else:
            self.log_result("GET /api/cart (after modifications)", False, "Failed to verify cart after modifications", str(data))
    
    def test_product_review_apis(self):
        """Test Product Review APIs"""
        print("\n⭐ Testing Product Review APIs...")
        
        if not self.product_ids:
            self.log_result("Review Tests", False, "No products available for review testing")
            return
        
        product_id = self.product_ids[0]
        
        # Test 1: Add a review
        review_data = {
            "rating": 5,
            "comment": "Excellent product! Highly recommend it. Great quality and fast shipping.",
            "session_id": self.session_id
        }
        
        success, data, status = self.make_request("POST", f"/products/{product_id}/reviews?rating=5&comment=Excellent product! Highly recommend it. Great quality and fast shipping.&session_id={self.session_id}")
        if success:
            self.log_result("POST /api/products/{id}/reviews", True, "Product review added successfully")
        else:
            self.log_result("POST /api/products/{id}/reviews", False, "Failed to add product review", str(data))
        
        # Add another review
        success, data, status = self.make_request("POST", f"/products/{product_id}/reviews?rating=4&comment=Good product, but could be better.&session_id={self.session_id}_2")
        if success:
            self.log_result("POST /api/products/{id}/reviews (second)", True, "Second review added successfully")
        else:
            self.log_result("POST /api/products/{id}/reviews (second)", False, "Failed to add second review", str(data))
        
        # Test 2: Get product reviews
        success, data, status = self.make_request("GET", f"/products/{product_id}/reviews")
        if success and isinstance(data, list):
            reviews_count = len(data)
            self.log_result("GET /api/products/{id}/reviews", True, f"Retrieved {reviews_count} reviews for product")
        else:
            self.log_result("GET /api/products/{id}/reviews", False, "Failed to get product reviews", str(data))
        
        # Test 3: Test invalid rating
        success, data, status = self.make_request("POST", f"/products/{product_id}/reviews?rating=6&comment=Invalid rating test&session_id={self.session_id}_3")
        if not success and status == 400:
            self.log_result("POST /api/products/{id}/reviews (invalid rating)", True, "Correctly rejected invalid rating")
        else:
            self.log_result("POST /api/products/{id}/reviews (invalid rating)", False, "Should have rejected invalid rating", str(data))
    
    def test_order_management_apis(self):
        """Test Order Management APIs"""
        print("\n📦 Testing Order Management APIs...")
        
        # Test 1: Get orders for authenticated user
        success, data, status = self.make_request("GET", "/orders")
        if success and isinstance(data, list):
            orders_count = len(data)
            self.log_result("GET /api/orders (authenticated)", True, f"Retrieved {orders_count} orders for authenticated user")
        else:
            self.log_result("GET /api/orders (authenticated)", False, "Failed to get orders for authenticated user", str(data))
        
        # Test 2: Get orders by session_id (guest user)
        # Remove auth token temporarily
        temp_token = self.auth_token
        self.auth_token = None
        
        success, data, status = self.make_request("GET", f"/orders?session_id={self.session_id}")
        if success and isinstance(data, list):
            session_orders_count = len(data)
            self.log_result("GET /api/orders (session_id)", True, f"Retrieved {session_orders_count} orders for session")
        else:
            self.log_result("GET /api/orders (session_id)", False, "Failed to get orders by session_id", str(data))
        
        # Restore auth token
        self.auth_token = temp_token
        
        # Test 3: Test unauthorized access (no auth and no session_id)
        self.auth_token = None
        success, data, status = self.make_request("GET", "/orders")
        if not success and status == 401:
            self.log_result("GET /api/orders (unauthorized)", True, "Correctly rejected unauthorized access")
        else:
            self.log_result("GET /api/orders (unauthorized)", False, "Should have rejected unauthorized access", str(data))
        
        # Restore auth token
        self.auth_token = temp_token
    
    def test_stripe_payment_apis(self):
        """Test Stripe Payment APIs (without completing actual payment)"""
        print("\n💳 Testing Stripe Payment APIs...")
        
        # Ensure we have items in cart for checkout
        if not self.cart_item_ids:
            # Add an item to cart first
            if self.product_ids:
                product_id = self.product_ids[0]
                success, data, status = self.make_request("POST", f"/cart/add?product_id={product_id}&quantity=1&session_id={self.session_id}")
                if not success:
                    self.log_result("Stripe Tests Setup", False, "Failed to add item to cart for checkout test")
                    return
        
        # Test 1: Create checkout session
        success, data, status = self.make_request("POST", f"/checkout/session?session_id={self.session_id}")
        if success and "url" in data and "session_id" in data:
            stripe_session_id = data["session_id"]
            checkout_url = data["url"]
            self.log_result("POST /api/checkout/session", True, f"Checkout session created successfully")
            
            # Test 2: Get checkout status
            success, status_data, status_code = self.make_request("GET", f"/checkout/status/{stripe_session_id}")
            if success and "status" in status_data:
                payment_status = status_data.get("payment_status", "unknown")
                self.log_result("GET /api/checkout/status/{id}", True, f"Retrieved checkout status: {payment_status}")
            else:
                self.log_result("GET /api/checkout/status/{id}", False, "Failed to get checkout status", str(status_data))
        else:
            self.log_result("POST /api/checkout/session", False, "Failed to create checkout session", str(data))
        
        # Test 3: Test checkout with empty cart
        empty_session_id = f"empty_session_{int(time.time())}"
        success, data, status = self.make_request("POST", f"/checkout/session?session_id={empty_session_id}")
        if not success and status == 400:
            self.log_result("POST /api/checkout/session (empty cart)", True, "Correctly rejected empty cart checkout")
        else:
            self.log_result("POST /api/checkout/session (empty cart)", False, "Should have rejected empty cart checkout", str(data))
    
    def test_error_handling(self):
        """Test various error scenarios"""
        print("\n🚨 Testing Error Handling...")
        
        # Test 1: Non-existent product
        fake_product_id = str(uuid.uuid4())
        success, data, status = self.make_request("GET", f"/products/{fake_product_id}")
        if not success and status == 404:
            self.log_result("GET /api/products/{fake_id}", True, "Correctly returned 404 for non-existent product")
        else:
            self.log_result("GET /api/products/{fake_id}", False, "Should have returned 404 for non-existent product", str(data))
        
        # Test 2: Invalid cart item update
        fake_item_id = str(uuid.uuid4())
        success, data, status = self.make_request("PUT", f"/cart/update/{fake_item_id}?quantity=1")
        if not success and status == 404:
            self.log_result("PUT /api/cart/update/{fake_id}", True, "Correctly returned 404 for non-existent cart item")
        else:
            self.log_result("PUT /api/cart/update/{fake_id}", False, "Should have returned 404 for non-existent cart item", str(data))
        
        # Test 3: Unauthorized access to protected route
        temp_token = self.auth_token
        self.auth_token = None
        success, data, status = self.make_request("GET", "/auth/me")
        if not success and status in [401, 403]:
            self.log_result("GET /api/auth/me (no auth)", True, "Correctly rejected unauthorized access")
        else:
            self.log_result("GET /api/auth/me (no auth)", False, "Should have rejected unauthorized access", str(data))
        
        self.auth_token = temp_token
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive E-Commerce Backend API Testing")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🆔 Session ID: {self.session_id}")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run test suites in order
        self.test_product_catalog_apis()
        self.test_user_authentication_apis()
        self.test_shopping_cart_apis()
        self.test_product_review_apis()
        self.test_order_management_apis()
        self.test_stripe_payment_apis()
        self.test_error_handling()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate summary
        self.generate_summary(duration)
    
    def generate_summary(self, duration: float):
        """Generate test summary"""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")
                    if result["details"]:
                        print(f"     Details: {result['details']}")
        
        print(f"\n🎯 CRITICAL API STATUS:")
        api_groups = {
            "Product Catalog": ["GET /api/products", "GET /api/products/{id}", "GET /api/categories"],
            "Authentication": ["POST /api/auth/register", "POST /api/auth/login", "GET /api/auth/me"],
            "Shopping Cart": ["POST /api/cart/add", "GET /api/cart/{session_id}", "PUT /api/cart/update/{item_id}"],
            "Reviews": ["POST /api/products/{id}/reviews", "GET /api/products/{id}/reviews"],
            "Orders": ["GET /api/orders (authenticated)", "GET /api/orders (session_id)"],
            "Payments": ["POST /api/checkout/session", "GET /api/checkout/status/{id}"]
        }
        
        for group_name, test_names in api_groups.items():
            group_results = [r for r in self.test_results if any(test_name in r["test"] for test_name in test_names)]
            if group_results:
                group_passed = sum(1 for r in group_results if r["success"])
                group_total = len(group_results)
                status = "✅" if group_passed == group_total else "❌" if group_passed == 0 else "⚠️"
                print(f"   {status} {group_name}: {group_passed}/{group_total} tests passed")

if __name__ == "__main__":
    tester = ECommerceAPITester()
    tester.run_all_tests()