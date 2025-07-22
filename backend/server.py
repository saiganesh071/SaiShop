from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe setup
stripe_api_key = os.environ.get('STRIPE_API_KEY')

# JWT settings
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-here-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# Create the main app without a prefix
app = FastAPI(title="E-Commerce API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    category: str
    image_url: str
    stock: int
    rating: float = 0.0
    reviews_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CartItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str
    product_id: str
    quantity: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    status: str = "pending"
    payment_status: str = "pending"
    stripe_session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: Optional[str] = None
    amount: float
    currency: str
    payment_status: str = "pending"
    stripe_session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    user_id: Optional[str] = None
    session_id: str
    rating: int
    comment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Auth helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def clean_mongo_doc(doc):
    """Remove MongoDB ObjectId and other non-serializable fields"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [clean_mongo_doc(item) for item in doc]
    if isinstance(doc, dict):
        cleaned = {}
        for key, value in doc.items():
            if key == '_id':
                continue  # Skip MongoDB ObjectId
            cleaned[key] = clean_mongo_doc(value)
        return cleaned
    return doc

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[User]:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user_doc = await db.users.find_one({"id": user_id})
        if user_doc:
            return User(**user_doc)
        return None
    except jwt.PyJWTError:
        return None

# Initialize sample products
async def init_sample_data():
    # Check if products already exist
    existing_products = await db.products.count_documents({})
    if existing_products > 0:
        return

    sample_products = [
        # Electronics
        {
            "id": str(uuid.uuid4()),
            "name": "Wireless Headphones",
            "description": "Premium wireless headphones with noise cancellation and 30-hour battery life.",
            "price": 199.99,
            "category": "electronics",
            "image_url": "https://images.unsplash.com/photo-1498049794561-7780e7231661?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxlbGVjdHJvbmljc3xlbnwwfHx8fDE3NTMyMDU4MTd8MA&ixlib=rb-4.1.0&q=85",
            "stock": 50,
            "rating": 4.5,
            "reviews_count": 128,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Smart Arduino Kit",
            "description": "Complete Arduino starter kit with sensors, LED strips, and programming guide.",
            "price": 89.99,
            "category": "electronics",
            "image_url": "https://images.unsplash.com/photo-1603732551658-5fabbafa84eb?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwyfHxlbGVjdHJvbmljc3xlbnwwfHx8fDE3NTMyMDU4MTd8MA&ixlib=rb-4.1.0&q=85",
            "stock": 30,
            "rating": 4.2,
            "reviews_count": 89,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "MacBook Pro 16\"",
            "description": "Latest MacBook Pro with M3 chip, 16GB RAM, and 512GB SSD. Perfect for professionals.",
            "price": 2499.99,
            "category": "electronics",
            "image_url": "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwzfHxlbGVjdHJvbmljc3xlbnwwfHx8fDE3NTMyMDU4MTd8MA&ixlib=rb-4.1.0&q=85",
            "stock": 15,
            "rating": 4.8,
            "reviews_count": 324,
            "created_at": datetime.utcnow()
        },
        # Clothing
        {
            "id": str(uuid.uuid4()),
            "name": "Designer Dress Collection",
            "description": "Elegant designer dress perfect for special occasions. Available in multiple colors and sizes.",
            "price": 159.99,
            "category": "clothing",
            "image_url": "https://images.unsplash.com/photo-1441984904996-e0b6ba687e04?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwxfHxjbG90aGluZ3xlbnwwfHx8fDE3NTMyMDU4MjN8MA&ixlib=rb-4.1.0&q=85",
            "stock": 40,
            "rating": 4.6,
            "reviews_count": 156,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Summer Fashion Set",
            "description": "Comfortable and stylish summer outfit set. Includes top, bottom, and accessories.",
            "price": 79.99,
            "category": "clothing",
            "image_url": "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwyfHxjbG90aGluZ3xlbnwwfHx8fDE3NTMyMDU4MjN8MA&ixlib=rb-4.1.0&q=85",
            "stock": 60,
            "rating": 4.3,
            "reviews_count": 92,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Casual Shirt Collection",
            "description": "High-quality casual shirts in various colors. Perfect for everyday wear.",
            "price": 34.99,
            "category": "clothing",
            "image_url": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwzfHxjbG90aGluZ3xlbnwwfHx8fDE3NTMyMDU4MjN8MA&ixlib=rb-4.1.0&q=85",
            "stock": 80,
            "rating": 4.1,
            "reviews_count": 67,
            "created_at": datetime.utcnow()
        },
        # Home Essentials
        {
            "id": str(uuid.uuid4()),
            "name": "Bathroom Essentials Set",
            "description": "Complete bathroom organizer set with premium quality containers and accessories.",
            "price": 49.99,
            "category": "home_essentials",
            "image_url": "https://images.unsplash.com/photo-1691057185806-ea8b5b9a4506?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwxfHxob21lJTIwZXNzZW50aWFsc3xlbnwwfHx8fDE3NTMyMDU4MzJ8MA&ixlib=rb-4.1.0&q=85",
            "stock": 35,
            "rating": 4.4,
            "reviews_count": 78,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Home Cleaning Kit",
            "description": "Professional-grade cleaning supplies for a spotless home. Eco-friendly and effective.",
            "price": 29.99,
            "category": "home_essentials",
            "image_url": "https://images.unsplash.com/photo-1528740561666-dc2479dc08ab?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwyfHxob21lJTIwZXNzZW50aWFsc3xlbnwwfHx8fDE3NTMyMDU4MzJ8MA&ixlib=rb-4.1.0&q=85",
            "stock": 70,
            "rating": 4.2,
            "reviews_count": 103,
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Home Office Setup",
            "description": "Complete home office essentials including desk organizers, lighting, and accessories.",
            "price": 199.99,
            "category": "home_essentials",
            "image_url": "https://images.unsplash.com/photo-1622992412846-99541b8e89b2?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwzfHxob21lJTIwZXNzZW50aWFsc3xlbnwwfHx8fDE3NTMyMDU4MzJ8MA&ixlib=rb-4.1.0&q=85",
            "stock": 25,
            "rating": 4.7,
            "reviews_count": 145,
            "created_at": datetime.utcnow()
        }
    ]

    await db.products.insert_many(sample_products)

# Routes
@api_router.post("/auth/register", response_model=UserResponse)
async def register_user(user_create: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_create.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = hash_password(user_create.password)
    user = User(
        email=user_create.email,
        full_name=user_create.full_name,
        hashed_password=hashed_password
    )
    
    await db.users.insert_one(user.dict())
    return UserResponse(**user.dict())

@api_router.post("/auth/login")
async def login_user(user_login: UserLogin):
    user_doc = await db.users.find_one({"email": user_login.email})
    if not user_doc or not verify_password(user_login.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_doc["id"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user_doc)
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserResponse(**current_user.dict())

@api_router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, search: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    products = await db.products.find(query).to_list(100)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.get("/categories")
async def get_categories():
    categories = await db.products.distinct("category")
    return {"categories": categories}

@api_router.post("/cart/add")
async def add_to_cart(product_id: str, quantity: int, session_id: str, current_user: Optional[User] = Depends(get_current_user)):
    # Check if product exists and has enough stock
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["stock"] < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock available")
    
    # Check if item already in cart
    existing_item = await db.cart_items.find_one({
        "product_id": product_id,
        "session_id": session_id
    })
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item["quantity"] + quantity
        if product["stock"] < new_quantity:
            raise HTTPException(status_code=400, detail="Not enough stock available")
        
        await db.cart_items.update_one(
            {"id": existing_item["id"]},
            {"$set": {"quantity": new_quantity}}
        )
    else:
        # Add new item
        cart_item = CartItem(
            user_id=current_user.id if current_user else None,
            session_id=session_id,
            product_id=product_id,
            quantity=quantity
        )
        await db.cart_items.insert_one(cart_item.dict())
    
    return {"message": "Item added to cart"}

@api_router.get("/cart/{session_id}")
async def get_cart(session_id: str):
    cart_items = await db.cart_items.find({"session_id": session_id}).to_list(100)
    
    # Get product details for each item
    cart_with_products = []
    total_amount = 0
    
    for item in cart_items:
        product = await db.products.find_one({"id": item["product_id"]})
        if product:
            item_total = product["price"] * item["quantity"]
            total_amount += item_total
            cart_with_products.append({
                **item,
                "product": product,
                "item_total": item_total
            })
    
    return {
        "items": cart_with_products,
        "total_amount": total_amount,
        "items_count": len(cart_with_products)
    }

@api_router.put("/cart/update/{item_id}")
async def update_cart_item(item_id: str, quantity: int):
    if quantity <= 0:
        await db.cart_items.delete_one({"id": item_id})
        return {"message": "Item removed from cart"}
    
    # Check stock
    item = await db.cart_items.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    product = await db.products.find_one({"id": item["product_id"]})
    if product and product["stock"] < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock available")
    
    await db.cart_items.update_one(
        {"id": item_id},
        {"$set": {"quantity": quantity}}
    )
    return {"message": "Cart updated"}

@api_router.delete("/cart/remove/{item_id}")
async def remove_cart_item(item_id: str):
    await db.cart_items.delete_one({"id": item_id})
    return {"message": "Item removed from cart"}

@api_router.post("/checkout/session")
async def create_checkout_session(request: Request, session_id: str, current_user: Optional[User] = Depends(get_current_user)):
    # Get cart items
    cart_items = await db.cart_items.find({"session_id": session_id}).to_list(100)
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate total and prepare order items
    order_items = []
    total_amount = 0
    
    for item in cart_items:
        product = await db.products.find_one({"id": item["product_id"]})
        if product:
            if product["stock"] < item["quantity"]:
                raise HTTPException(status_code=400, detail=f"Not enough stock for {product['name']}")
            
            item_total = product["price"] * item["quantity"]
            total_amount += item_total
            order_items.append({
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "quantity": item["quantity"],
                "item_total": item_total
            })
    
    if total_amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid cart total")
    
    # Get host URL from request
    host_url = str(request.base_url).rstrip('/')
    success_url = f"{host_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/cart"
    
    # Initialize Stripe checkout
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Create checkout session request
    checkout_request = CheckoutSessionRequest(
        amount=total_amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "session_id": session_id,
            "user_id": current_user.id if current_user else "",
            "order_type": "cart_checkout"
        }
    )
    
    # Create Stripe session
    stripe_session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    payment_transaction = PaymentTransaction(
        session_id=session_id,
        user_id=current_user.id if current_user else None,
        amount=total_amount,
        currency="usd",
        payment_status="pending",
        stripe_session_id=stripe_session.session_id,
        metadata={"order_items": order_items}
    )
    await db.payment_transactions.insert_one(payment_transaction.dict())
    
    # Create order record
    order = Order(
        user_id=current_user.id if current_user else None,
        session_id=session_id,
        items=order_items,
        total_amount=total_amount,
        status="pending",
        payment_status="pending",
        stripe_session_id=stripe_session.session_id
    )
    await db.orders.insert_one(order.dict())
    
    return {"url": stripe_session.url, "session_id": stripe_session.session_id}

@api_router.get("/checkout/status/{stripe_session_id}")
async def get_checkout_status(stripe_session_id: str):
    # Initialize Stripe checkout
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    # Get status from Stripe
    checkout_status = await stripe_checkout.get_checkout_status(stripe_session_id)
    
    # Update payment transaction
    transaction = await db.payment_transactions.find_one({"stripe_session_id": stripe_session_id})
    if transaction and transaction["payment_status"] != "paid":
        if checkout_status.payment_status == "paid":
            # Update transaction
            await db.payment_transactions.update_one(
                {"stripe_session_id": stripe_session_id},
                {"$set": {"payment_status": "paid"}}
            )
            
            # Update order
            await db.orders.update_one(
                {"stripe_session_id": stripe_session_id},
                {"$set": {"status": "confirmed", "payment_status": "paid"}}
            )
            
            # Reduce product stock and clear cart
            order = await db.orders.find_one({"stripe_session_id": stripe_session_id})
            if order:
                for item in order["items"]:
                    await db.products.update_one(
                        {"id": item["product_id"]},
                        {"$inc": {"stock": -item["quantity"]}}
                    )
                
                # Clear cart for this session
                await db.cart_items.delete_many({"session_id": order["session_id"]})
    
    return {
        "status": checkout_status.status,
        "payment_status": checkout_status.payment_status,
        "amount_total": checkout_status.amount_total,
        "currency": checkout_status.currency
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        # Initialize Stripe checkout
        stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.event_type == "checkout.session.completed":
            # Handle successful payment
            await db.payment_transactions.update_one(
                {"stripe_session_id": webhook_response.session_id},
                {"$set": {"payment_status": "paid"}}
            )
            
            await db.orders.update_one(
                {"stripe_session_id": webhook_response.session_id},
                {"$set": {"status": "confirmed", "payment_status": "paid"}}
            )
        
        return {"received": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/orders")
async def get_orders(current_user: Optional[User] = Depends(get_current_user), session_id: Optional[str] = None):
    query = {}
    if current_user:
        query["user_id"] = current_user.id
    elif session_id:
        query["session_id"] = session_id
    else:
        raise HTTPException(status_code=401, detail="Authentication or session_id required")
    
    orders = await db.orders.find(query).sort("created_at", -1).to_list(50)
    return [Order(**order) for order in orders]

@api_router.post("/products/{product_id}/reviews")
async def add_review(product_id: str, rating: int, comment: str, session_id: str, current_user: Optional[User] = Depends(get_current_user)):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if product exists
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create review
    review = Review(
        product_id=product_id,
        user_id=current_user.id if current_user else None,
        session_id=session_id,
        rating=rating,
        comment=comment
    )
    await db.reviews.insert_one(review.dict())
    
    # Update product rating
    reviews = await db.reviews.find({"product_id": product_id}).to_list(1000)
    avg_rating = sum([r["rating"] for r in reviews]) / len(reviews)
    
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"rating": round(avg_rating, 1), "reviews_count": len(reviews)}}
    )
    
    return {"message": "Review added successfully"}

@api_router.get("/products/{product_id}/reviews")
async def get_product_reviews(product_id: str):
    reviews = await db.reviews.find({"product_id": product_id}).sort("created_at", -1).to_list(100)
    return [Review(**review) for review in reviews]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await init_sample_data()
    logger.info("E-commerce API started successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()