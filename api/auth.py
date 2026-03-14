import os
from dotenv import load_dotenv
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

load_dotenv()

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(_API_KEY_HEADER)) -> str:
    expected = os.getenv("IWR_API_KEY")
    if not expected:
        raise RuntimeError("IWR_API_KEY is not set in environment")
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return api_key
