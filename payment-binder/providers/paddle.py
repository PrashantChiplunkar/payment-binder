from base_provider import BaseAPIClient, PaymentProvider
from typing import Optional, Dict, Any


class PaddleClient(BaseAPIClient, PaymentProvider):
    """
    Client for integrating with Paddle payment services.
    """

    def __init__(self, api_secret: Optional[str] = None):
        """
        Initialize the Paddle client.
        
        Args:
            api_secret: Optional API secret (defaults to config value)
        """
        super().__init__(
            base_url=loaded_config.paddle_api_base_url,
            api_secret=api_secret or loaded_config.paddle_api_secret,
            auth_method=AuthMethod.BEARER
        )

    async def create_transaction(
        self, 
        plan_details: PlanSchema, 
        subscription_id: str, 
        user_data: UserData
    ) -> APIResponse:
        """
        Create a new transaction on Paddle.
        
        Args:
            plan_details: Details of the plan
            subscription_id: ID of the subscription
            user_data: User data for the transaction
            
        Returns:
            Standardized API response
        """
        try:
            body = {
                "items": [{
                    "price_id": plan_details.psp_price_id,
                    "quantity": 1
                }],
                "customer": {
                    "email": user_data.email
                },
                "custom_data": {
                    "plan_id": str(plan_details.id),
                    "subscription_id": str(subscription_id)
                }
            }
            
            response = await self._make_request("POST", "/transactions", body)
            
            return APIResponse(
                success=True,
                data={
                    "transaction_id": response.get("data", {}).get("id"),
                    "checkout_url": response.get("data", {}).get("checkout_url")
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )

    async def create_plan(self, plan_details: PlanSchema) -> APIResponse:
        """
        Create a new plan on Paddle.
        
        Args:
            plan_details: Details of the plan to create
            
        Returns:
            Standardized API response with product and price IDs
        """
        try:
            # Create the product first
            product_payload = {
                "name": plan_details.name,
                "tax_category": "digital-goods",
                "description": plan_details.description or plan_details.name
            }
            product = await self._make_request("POST", "/products", product_payload)

            # Then create the price for the product
            price_payload = {
                "name": plan_details.name,
                "product_id": product["data"]["id"],
                "description": plan_details.description or plan_details.name,
                "unit_price": {
                    "amount": plan_details.amount,
                    "currency_code": plan_details.currency or "USD"
                },
                "billing_cycle": {
                    "interval": self._map_billing_cycle(plan_details.billing_cycle),
                    "frequency": 1
                },
                "tax_mode": "account_setting",
                "quantity": {
                    "minimum": 1,
                    "maximum": 1
                }
            }
            price = await self._make_request("POST", "/prices", price_payload)
            
            return APIResponse(
                success=True,
                data={
                    "product_id": product["data"]["id"],
                    "price_id": price["data"]["id"]
                },
                raw_response={
                    "product": product,
                    "price": price
                }
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )

    def _map_billing_cycle(self, billing_cycle: str) -> str:
        """Map internal billing cycle to Paddle-specific format."""
        mapping = {
            "daily": "day",
            "weekly": "week",
            "monthly": "month", 
            "yearly": "year"
        }
        return mapping.get(billing_cycle.lower(), "month")

    async def get_transaction_invoice(self, transaction_id: str) -> APIResponse:
        """
        Get invoice details for a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            Standardized API response with invoice details
        """
        try:
            response = await self._make_request("GET", f"/transactions/{transaction_id}/invoice")
            
            return APIResponse(
                success=True,
                data={
                    "invoice_url": response.get("data", {}).get("invoice_url"),
                    "invoice_id": response.get("data", {}).get("id")
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )

    async def get_subscription_details(self, subscription_id: str) -> APIResponse:
        """
        Get details of a subscription.
        
        Args:
            subscription_id: ID of the subscription
            
        Returns:
            Standardized API response with subscription details
        """
        try:
            response = await self._make_request("GET", f"/subscriptions/{subscription_id}")
            
            subscription_data = response.get("data", {})
            
            return APIResponse(
                success=True,
                data=self._normalize_subscription_details(subscription_data),
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )
            
    def _normalize_subscription_details(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Paddle subscription format to standardized format."""
        return {
            "id": subscription_data.get("id"),
            "status": subscription_data.get("status"),
            "created_at": subscription_data.get("created_at"),
            "next_billing_date": subscription_data.get("next_billed_at"),
            "plan_id": subscription_data.get("items", [{}])[0].get("price_id") if subscription_data.get("items") else None,
            "customer_id": subscription_data.get("customer_id")
        }

    async def end_subscription(self, subscription_id: str) -> APIResponse:
        """
        End a subscription on Paddle.
        
        Args:
            subscription_id: ID of the subscription to end
            
        Returns:
            Standardized API response
        """
        try:
            payload = {
                "effective_from": "next_billing_period"
            }

            response = await self._make_request("POST", f"/subscriptions/{subscription_id}/cancel", payload)
            
            return APIResponse(
                success=True,
                data={
                    "subscription_id": subscription_id,
                    "status": "cancelled"
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )
            
    async def create_customer(self, user_data: UserData) -> APIResponse:
        """
        Create a customer on Paddle.
        
        Args:
            user_data: User data for customer creation
            
        Returns:
            Standardized API response with customer details
        """
        try:
            customer_payload = {
                "email": user_data.email,
                "name": f"{user_data.firstName} {user_data.lastName}"
            }
            
            response = await self._make_request("POST", "/customers", customer_payload)
            
            return APIResponse(
                success=True,
                data={
                    "customer_id": response.get("data", {}).get("id")
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )
