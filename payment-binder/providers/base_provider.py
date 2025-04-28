from abc import ABC, abstractmethod
from schemas import AuthMethod, APIResponse
from typing import Dict, Any, Optional
import httpx
import asyncio
from exceptions import APIError
from logger import logger


class BaseAPIClient(ABC):
    """
    Abstract base class for API clients to handle common operations.
    
    This class provides the foundation for all payment provider clients,
    with standardized request handling, retry logic, and error handling.
    """

    def __init__(
        self, 
        base_url: str, 
        api_secret: str, 
        auth_method: AuthMethod = AuthMethod.BASIC,
        timeout: float = 30.0
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the API
            api_secret: API secret or token
            auth_method: Authentication method to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.api_secret = api_secret
        self.timeout = timeout
        self.headers = self._build_headers(auth_method)
    
    def _build_headers(self, auth_method: AuthMethod) -> Dict[str, str]:
        """Build request headers based on the authentication method."""
        headers = {"Content-Type": "application/json"}
        
        if auth_method in (AuthMethod.BASIC, AuthMethod.BEARER):
            headers["Authorization"] = f"{auth_method} {self.api_secret}"
        elif auth_method == AuthMethod.API_KEY:
            headers["X-Api-Key"] = self.api_secret
            
        return headers

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
        backoff_factor: float = 1.5
    ) -> Dict[str, Any]:
        """
        Makes an HTTP request with retry logic.

        Args:
            method: HTTP method (e.g., GET, POST)
            endpoint: API endpoint
            json: JSON payload for the request
            params: Query parameters
            retries: Number of retry attempts
            backoff_factor: Time in seconds to wait between retries

        Returns:
            The parsed JSON response

        Raises:
            APIError: If the API call fails after all retries
        """
        url = f"{self.base_url}{endpoint}"
        attempt = 0

        while attempt < retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method, 
                        url, 
                        headers=self.headers, 
                        json=json,
                        params=params
                    )

                if response.status_code in (200, 201, 202):
                    if attempt > 1:
                        logger.info(
                            "API call succeeded on retry %d: %s %s",
                            attempt, method, url
                        )
                    else:
                        logger.debug(
                            "API call succeeded: %s %s",
                            method, url
                        )
                    return response.json()

                logger.error(
                    "API call failed: %s %s [Status Code: %d] Response: %s",
                    method, url, response.status_code, response.text
                )
                
                # If this was our last retry, raise an error
                if attempt >= retries:
                    raise APIError(
                        message="API call failed after retries", 
                        status_code=response.status_code, 
                        response_text=response.text
                    )

            except httpx.RequestError as exc:
                if attempt < retries:
                    wait_time = backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "Request error during API call: %s %s. Attempt %d/%d. Retrying in %.2f seconds. Error: %s",
                        method, url, attempt, retries, wait_time, str(exc)
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Exhausted all retries for API call: %s %s. Error: %s",
                        method, url, str(exc)
                    )
                    raise APIError(f"Request error after retries: {str(exc)}")




class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.
    
    This interface defines the standard operations that all payment
    providers must implement, ensuring consistency across different
    payment gateways.
    """
    
    @abstractmethod
    async def create_transaction(self, plan_details, subscription_id: str, user_data) -> APIResponse:
        """Create a new transaction."""
        pass
    
    @abstractmethod
    async def create_plan(self, plan_details) -> APIResponse:
        """Create a new plan on the payment provider."""
        pass
    
    @abstractmethod
    async def get_transaction_invoice(self, transaction_id: str) -> APIResponse:
        """Get invoice details for a transaction."""
        pass
    
    @abstractmethod
    async def get_subscription_details(self, subscription_id: str) -> APIResponse:
        """Get details of a subscription."""
        pass
    
    @abstractmethod
    async def end_subscription(self, subscription_id: str) -> APIResponse:
        """End a subscription."""
        pass
    
    @abstractmethod
    async def create_customer(self, user_data) -> APIResponse:
        """Create a customer on the payment provider."""
        pass
