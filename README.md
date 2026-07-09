# 🎬 Online Cinema API

A robust, production-ready RESTful API backend for an Online Cinema platform. The system supports full user lifecycle management, dynamic movie catalogs with multi-faceted filtering, a relational shopping cart, secure order processing, and Stripe payment integration. Containerized with Docker and optimized with asynchronous task processing.



---

## 🛠 Tech Stack

* **Backend Framework:** FastAPI (Asynchronous Python)
* **Database & ORM:** PostgreSQL, SQLAlchemy (Async)
* **Caching & Broker:** Redis
* **Background Tasks:** Celery & Celery-Beat (Scheduled tasks)
* **Payment Gateway:** Stripe API (via Webhooks)
* **Containerization:** Docker & Docker Compose
* **Authentication:** JWT (Access & Refresh Tokens)

---

## 🚀 Key Features & System Architecture

### 1. Authentication & User Management (`/auth`, `/users`)
* **Secure Registration:** Email uniqueness validation with auto-generated activation tokens.
* **Background Activation Email:** Handled via Celery to ensure non-blocking user experience. 24-hour token expiration with a resend mechanism.
* **Automated Cleanup:** `celery-beat` periodically sweeps and deletes expired activation tokens.
* **JWT Token Management:** Returns Access & Refresh tokens on login. Logout safely revokes and deletes the Refresh Token.
* **Role-Based Access Control (RBAC):** Three distinct user groups:
    * `USER`: Basic interface interaction, catalog browsing, and ordering.
    * `MODERATOR`: Full CRUD operations on movies/genres/actors.
    * `ADMIN`: Total control over users, manual activation, and role modification.

### 2. Movies Catalog Engine (`/movies`)
* **Advanced Filtering & Sorting:** Dynamic lookups by release year, IMDb rating, prices, popularity, and genres.
* **Full-Text Search:** Query movies by title, description, actors (`Stars`), or `Directors`.
* **Social Interactions:** 10-point scale movie rating, likes/dislikes, user comments, and an asynchronous notification system for comment replies/likes.
* **Safety Constraints:** Strict database constraints (Unique `name` + `year` + `time`). Moderators cannot delete a movie if it has been purchased by at least one user.

### 3. Relational Shopping Cart (`/cart`)
* **State Control:** Strict 1:1 relationship between `User` and `Cart`.
* **Validation Layer:** Prevents duplicate items in the same cart, blocks purchasing already-owned movies, and forces guest authentication before checkout.
* **Admin Diagnostics:** Administrators can inspect user carts for troubleshooting purposes.

### 4. Order Management & Verification (`/orders`)
* **Snapshot Integrity:** The `OrderItem` model stores `price_at_order` to safeguard financial history against future catalog price changes.
* **State Machine:** Orders track lifecycle statuses (`pending`, `paid`, `canceled`).
* **Pre-checkout Validation:** Automatic re-validation of movie availability, duplicate pending checkouts, and total cost verification before routing to Stripe.

### 5. Stripe Payment Integration (`/payments`)
* **Stripe Webhooks:** Fully integrated webhook processing to dynamically capture transaction statuses (`successful`, `canceled`, `refunded`) and update corresponding order records securely.
* **Granular Financials:** `PaymentItem` mirrors order items at the exact point of payment for precise audit logs and itemized refund handling.


---

## 📦 Local Installation

The entire system (FastAPI app, PostgreSQL, Redis, Celery workers) is containerized and orchestrated via Docker Compose.

### Deployment Steps

1. **Clone the repository:**
```bash
git clone https://github.com/Rar571/Online-Cinema-API.git
cd online-cinema-api
```

2. **Configure Environment Variables:**
```bash
cp .env.sample .env
# Open .env and fill in your Stripe Keys, JWT Secret, and Email configurations.
```

3. **Spin up all services:**
```bash
docker-compose up --build
```

## API Documentation
Once the containers are running, you can access the interactive Swagger UI and explore the endpoints locally:

- Interactive Documentation: http://localhost:8000/docs

- Alternative Schema (Redoc): http://localhost:8000/redoc
