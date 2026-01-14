"""AWS Lambda handler for FastAPI application using Mangum.

This module provides the Lambda entry point for the Movie Ranking API.
Mangum wraps the FastAPI ASGI application for AWS Lambda compatibility.
"""

from mangum import Mangum

from app.main import app

# Mangum adapter for AWS Lambda
# lifespan="off" is required because Lambda doesn't support ASGI lifespan events
handler = Mangum(app, lifespan="off")
