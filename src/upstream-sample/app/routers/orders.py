"""
Orders Router - Customer Order Management with MongoDB Persistence

Endpoints:
- GET /api/orders - List all orders (chef, manager, admin)
- GET /api/orders/my - List customer's own orders (customer)
- GET /api/orders/{order_id} - Get order details (owner, chef, manager, admin)
- POST /api/orders - Place a new order (customer)
- POST /api/orders/{order_id}/pay - Pay for an order (order owner)
- POST /api/orders/{order_id}/cancel - Cancel an order

Scope Requirements (for OAuth2 scope-based access control):
- orders:read - Required for GET operations
- orders:write - Required for creating orders
- orders:pay - Required for payment operations
- orders:cancel - Required for cancel operations
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import (
    OrderCanceller,
    OrderPayer,
    OrderReader,
    OrderWriter,
    RoleAndScopeChecker,
    UserInfo,
)
from app.database import MENU_COLLECTION, ORDERS_COLLECTION, get_collection
from app.models.schemas import (
    MenuItem,
    OperationResponse,
    Order,
    OrderCreate,
    OrderItem,
    OrderStatus,
    PaymentRequest,
    PaymentResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Order Endpoints
# ============================================================================


@router.get(
    "",
    response_model=list[Order],
    summary="List all orders (Staff)",
    description="List all orders for kitchen/management view. **Requires chef, manager, or admin role AND `orders:read` scope.**",
    openapi_extra={
        "security": [{"oauth2": ["orders:read"]}],
    },
)
async def list_all_orders(
    user: Annotated[
        UserInfo,
        Depends(
            RoleAndScopeChecker(
                required_roles=["developer", "manager", "admin"],
                required_scopes=["orders:read"],
            )
        ),
    ],
    status_filter: OrderStatus | None = None,
) -> list[Order]:
    """List all orders (staff only)."""
    logger.info(f"Staff '{user.username}' listing all orders (status_filter={status_filter})")

    orders_col = get_collection(ORDERS_COLLECTION)

    # Build filter
    filter_query: dict = {}
    if status_filter:
        filter_query["status"] = status_filter.value

    # Fetch orders sorted by created_at descending
    cursor = orders_col.find(filter_query).sort("created_at", -1)
    orders = [Order(**doc) async for doc in cursor]

    return orders


@router.get(
    "/my",
    response_model=list[Order],
    summary="List my orders (Customer)",
    description="List the current customer's orders. **Requires customer role AND `orders:read` scope.**",
    openapi_extra={
        "security": [{"oauth2": ["orders:read"]}],
    },
)
async def list_my_orders(
    user: Annotated[UserInfo, Depends(OrderReader)],
) -> list[Order]:
    """List customer's own orders."""
    logger.info(f"Customer '{user.username}' listing their orders")

    orders_col = get_collection(ORDERS_COLLECTION)

    # Fetch customer's orders sorted by created_at descending
    cursor = orders_col.find({"customer_id": user.sub}).sort("created_at", -1)
    orders = [Order(**doc) async for doc in cursor]

    return orders


@router.get(
    "/{order_id}",
    response_model=Order,
    summary="Get order details",
    description="Get details of a specific order. Customers can only view their own orders. **Requires `orders:read` scope.**",
    openapi_extra={
        "security": [{"oauth2": ["orders:read"]}],
    },
)
async def get_order(
    order_id: str,
    user: Annotated[UserInfo, Depends(OrderReader)],
) -> Order:
    """Get order details."""
    logger.info(f"User '{user.username}' fetching order: {order_id}")

    orders_col = get_collection(ORDERS_COLLECTION)
    doc = await orders_col.find_one({"id": order_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = Order(**doc)

    # Check access: owner, chef, manager, or admin can view
    is_owner = order.customer_id == user.sub
    is_staff = user.has_any_role(["developer", "manager", "admin"])

    if not is_owner and not is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own orders",
        )

    return order


@router.post(
    "",
    response_model=Order,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
    description="Place a new order. **Requires customer role AND `orders:write` scope.**",
    openapi_extra={
        "security": [{"oauth2": ["orders:write"]}],
    },
)
async def create_order(
    order_data: OrderCreate,
    user: Annotated[UserInfo, Depends(OrderWriter)],
) -> Order:
    """Create a new order (customer only)."""
    logger.info(f"Customer '{user.username}' placing order with {len(order_data.items)} items")

    menu_col = get_collection(MENU_COLLECTION)
    orders_col = get_collection(ORDERS_COLLECTION)

    # Resolve order items and calculate totals
    order_items: list[OrderItem] = []
    total = 0.0

    for item in order_data.items:
        menu_doc = await menu_col.find_one({"id": item.menu_item_id})

        if not menu_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{item.menu_item_id}' not found",
            )

        menu_item = MenuItem(**menu_doc)

        if not menu_item.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' is currently unavailable",
            )

        subtotal = menu_item.unit_price_usd * item.quantity
        total += subtotal

        order_items.append(
            OrderItem(
                menu_item_id=item.menu_item_id,
                menu_item_name=menu_item.name,
                quantity=item.quantity,
                unit_price=menu_item.unit_price_usd,
                subtotal=subtotal,
                special_instructions=item.special_instructions,
            )
        )

    # Create order
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)

    order = Order(
        id=order_id,
        customer_id=user.sub,
        customer_username=user.username,
        items=order_items,
        status=OrderStatus.PENDING,
        total=round(total, 2),
        delivery_address=order_data.delivery_address,
        special_instructions=order_data.special_instructions,
        created_at=now,
        updated_at=now,
    )

    await orders_col.insert_one(order.model_dump())
    logger.info(f"Created order: {order_id} (total: ${order.total:.2f})")

    return order


@router.post(
    "/{order_id}/pay",
    response_model=PaymentResponse,
    summary="Pay for an order",
    description="Process payment for an order. **Only the order owner can pay. Requires `orders:pay` scope.**",
    openapi_extra={
        "security": [{"oauth2": ["orders:pay"]}],
    },
)
async def pay_for_order(
    order_id: str,
    payment: PaymentRequest,
    user: Annotated[UserInfo, Depends(OrderPayer)],
) -> PaymentResponse:
    """Pay for an order (order owner only)."""
    logger.info(f"Customer '{user.username}' paying for order: {order_id}")

    orders_col = get_collection(ORDERS_COLLECTION)
    doc = await orders_col.find_one({"id": order_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = Order(**doc)

    # Verify ownership
    if order.customer_id != user.sub and not user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only pay for your own orders",
        )

    # Check order status
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be paid. Current status: {order.status.value}",
        )

    # Simulate payment processing
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    # Update order status in database
    await orders_col.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.PAID.value,
                "updated_at": datetime.now(UTC),
            }
        },
    )

    logger.info(f"Payment processed for order {order_id}: ${order.total:.2f} via {payment.payment_method.value}")

    return PaymentResponse(
        order_id=order_id,
        amount=order.total,
        status="success",
        transaction_id=transaction_id,
        message=f"Payment of ${order.total:.2f} processed successfully via {payment.payment_method.value}",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OperationResponse,
    summary="Cancel an order",
    description="Cancel an order. Customers can cancel pending orders; managers can cancel any order. **Requires `orders:cancel` scope.**",
    openapi_extra={
        "security": [{"oauth2": ["orders:cancel"]}],
    },
)
async def cancel_order(
    order_id: str,
    user: Annotated[UserInfo, Depends(OrderCanceller)],
) -> OperationResponse:
    """Cancel an order."""
    logger.info(f"User '{user.username}' cancelling order: {order_id}")

    orders_col = get_collection(ORDERS_COLLECTION)
    doc = await orders_col.find_one({"id": order_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    order = Order(**doc)
    is_owner = order.customer_id == user.sub
    is_manager = user.has_any_role(["manager", "admin"])

    # Check access
    if not is_owner and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own orders",
        )

    # Customers can only cancel pending orders
    if is_owner and not is_manager:
        if order.status not in [OrderStatus.PENDING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only cancel pending orders. Contact management for other cancellations.",
            )

    # Managers can cancel any non-completed order
    if order.status in [OrderStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed order",
        )

    # Update order status in database
    await orders_col.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.CANCELLED.value,
                "updated_at": datetime.now(UTC),
            }
        },
    )

    logger.info(f"Order {order_id} cancelled by '{user.username}'")

    return OperationResponse(
        success=True,
        message=f"Order '{order_id}' cancelled successfully",
        order_id=order_id,
    )
