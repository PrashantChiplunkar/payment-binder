class RazorpayClient(BaseAPIClient, PaymentProvider):
    """
    Client for integrating with Razorpay payment services.
    """
    
    def __init__(self, api_secret: Optional[str] = None):
        """
        Initialize the Razorpay client.
        
        Args:
            api_secret: Optional API secret (defaults to config value)
        """
        super().__init__(
            base_url=loaded_config.razorpay_api_base_url,
            api_secret=api_secret or loaded_config.razorpay_api_secret,
            auth_method=AuthMethod.BASIC
        )

    async def create_transaction(
        self, 
        plan_details: PlanSchema, 
        subscription_id: str, 
        user_data: UserData
    ) -> APIResponse:
        """
        Create a new transaction on Razorpay.
        For Razorpay, this involves creating a subscription and getting its first invoice.
        
        Args:
            plan_details: Details of the plan
            subscription_id: ID of the subscription in our system
            user_data: User data for the transaction
            
        Returns:
            Standardized API response
        """
        try:
            # First, create or get customer
            customer_response = await self.create_customer(user_data)
            if not customer_response.success:
                return customer_response
                
            customer_id = customer_response.data.get("customer_id")
            
            # Create a subscription
            subscription_payload = {
                "plan_id": plan_details.psp_price_id,
                "total_count": 100,  # Default to 100 cycles
                "quantity": 1,
                "customer_notify": 1,
                "customer_id": customer_id,
                "notes": {
                    "internal_subscription_id": str(subscription_id),
                    "plan_id": str(plan_details.id)
                }
            }
            
            response = await self._make_request("POST", "/subscriptions", subscription_payload)
            
            # Get the first invoice from the subscription
            razorpay_subscription_id = response.get("id")
            invoice_id = response.get("invoice_id")
            
            return APIResponse(
                success=True,
                data={
                    "subscription_id": razorpay_subscription_id,
                    "invoice_id": invoice_id,
                    "checkout_url": response.get("short_url")
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
        Create a new plan on Razorpay.
        
        Args:
            plan_details: Details of the plan to create
            
        Returns:
            Standardized API response with plan ID
        """
        try:
            body = {
                "period": self._map_billing_cycle(plan_details.billing_cycle),
                "interval": 1,
                "item": {
                    "name": plan_details.name,
                    "amount": int(plan_details.amount),
                    "currency": plan_details.currency or "USD",
                    "description": plan_details.description or plan_details.name,
                }
            }
            
            response = await self._make_request("POST", "/plans", body)
            
            return APIResponse(
                success=True,
                data={
                    "plan_id": response.get("id")
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )
            
    def _map_billing_cycle(self, billing_cycle: str) -> str:
        """Map internal billing cycle to Razorpay-specific format."""
        mapping = {
            "daily": "daily",
            "weekly": "weekly",
            "monthly": "monthly", 
            "yearly": "yearly"
        }
        return mapping.get(billing_cycle.lower(), "monthly")

    async def get_transaction_invoice(self, invoice_id: str) -> APIResponse:
        """
        Get invoice details for a transaction.
        
        Args:
            invoice_id: ID of the invoice
            
        Returns:
            Standardized API response with invoice details
        """
        try:
            response = await self._make_request("GET", f"/invoices/{invoice_id}")
            
            return APIResponse(
                success=True,
                data={
                    "invoice_url": response.get("short_url"),
                    "invoice_id": response.get("id"),
                    "status": response.get("status")
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )

    async def issue_invoice(self, invoice_id: str) -> APIResponse:
        """
        Issue an invoice.
        
        Args:
            invoice_id: ID of the invoice to issue
            
        Returns:
            Standardized API response
        """
        try:
            response = await self._make_request("POST", f"/invoices/{invoice_id}/issue")
            
            return APIResponse(
                success=True,
                data={
                    "invoice_id": response.get("id"),
                    "status": response.get("status")
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )

    async def draft_invoice(
        self, 
        customer_id: str, 
        plan_name: str, 
        plan_amount: int, 
        plan_currency: str, 
        plan_description: str
    ) -> APIResponse:
        """
        Draft an invoice.
        
        Args:
            customer_id: ID of the customer
            plan_name: Name of the plan
            plan_amount: Amount of the plan
            plan_currency: Currency of the plan
            plan_description: Description of the plan
            
        Returns:
            Standardized API response with invoice details
        """
        try:
            body = {
                "type": "invoice",
                "date": DateHelper.convert_date_to_epoch(),
                "customer_id": customer_id,
                "line_items": [{
                    "name": plan_name,
                    "description": plan_description,
                    "amount": plan_amount,
                    "currency": plan_currency
                }],
                "expire_by": DateHelper.convert_date_to_epoch(
                    datetime.now(timezone.utc) + timedelta(days=2)
                ),
                "draft": 1
            }
            
            response = await self._make_request("POST", "/invoices", body)
            
            return APIResponse(
                success=True,
                data={
                    "invoice_id": response.get("id"),
                    "status": response.get("status")
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
            
            return APIResponse(
                success=True,
                data=self._normalize_subscription_details(response),
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )
            
    def _normalize_subscription_details(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Razorpay subscription format to standardized format."""
        return {
            "id": subscription_data.get("id"),
            "status": subscription_data.get("status"),
            "created_at": datetime.fromtimestamp(subscription_data.get("created_at", 0), tz=timezone.utc),
            "next_billing_date": datetime.fromtimestamp(subscription_data.get("current_end", 0), tz=timezone.utc),
            "plan_id": subscription_data.get("plan_id"),
            "customer_id": subscription_data.get("customer_id")
        }

    async def end_subscription(self, subscription_id: str) -> APIResponse:
        """
        End a subscription on Razorpay.
        
        Args:
            subscription_id: ID of the subscription to end
            
        Returns:
            Standardized API response
        """
        try:
            body = {"cancel_at_cycle_end": True}
            
            response = await self._make_request("POST", f"/subscriptions/{subscription_id}/cancel", body)
            
            return APIResponse(
                success=True,
                data={
                    "subscription_id": subscription_id,
                    "status": response.get("status")
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
        Create customer on Razorpay.
        
        Args:
            user_data: User data for customer creation
            
        Returns:
            Standardized API response with customer details
        """
        try:
            customer_payload = {
                "name": f"{user_data.firstName} {user_data.lastName}",
                "email": user_data.email,
                "fail_existing": 0  # Don't fail if customer already exists
            }
            
            response = await self._make_request("POST", "/customers", customer_payload)
            
            return APIResponse(
                success=True,
                data={
                    "customer_id": response.get("id")
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )

    async def get_payment_downtimes(self) -> APIResponse:
        """
        Get downtimes of the payments gateways.
        
        Returns:
            Standardized API response with downtime information
        """
        try:
            response = await self._make_request("GET", "/payments/downtimes")
            
            return APIResponse(
                success=True,
                data={
                    "downtimes": response.get("items", [])
                },
                raw_response=response
            )
        except APIError as e:
            return APIResponse(
                success=False,
                error=str(e)
            )
