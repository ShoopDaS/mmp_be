# MultiMusic Platform - Backend

Backend services for the MultiMusic Platform, handling OAuth authentication flows and token management for multiple streaming services.

## Overview

The backend is intentionally minimal, consisting of serverless Lambda functions that handle OAuth callbacks and token refresh operations. The architecture keeps API requests client-side to avoid rate limiting and improve performance.

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │────────▶│   Lambda     │────────▶│   Spotify   │
│  (Browser)  │         │  Functions   │         │     API     │
└─────────────┘         └──────────────┘         └─────────────┘
      │                                                  │
      │                                                  │
      └──────────────────────────────────────────────────┘
              Direct API calls with user token
```

**Key Principle**: The backend only handles authentication. All music-related API calls (search, playback, playlists) go directly from the frontend to the streaming service APIs using the user's access token.

## Why This Approach?

- **No rate limiting issues**: Each user uses their own API quota
- **Better performance**: No backend proxy bottleneck
- **Lower costs**: Minimal Lambda invocations
- **Scalability**: Frontend scales infinitely via CDN

## Tech Stack

**Primary Stack:**
- Python 3.13
- FastAPI (API framework)
- AWS Lambda (Python runtime)
- API Gateway (REST API)
- DynamoDB (token storage)
- AWS Secrets Manager (OAuth secrets)
- Boto3 (AWS SDK)

## API Endpoints

### Spotify Authentication

**POST /auth/spotify/login**
- Initiates Spotify OAuth flow
- Returns authorization URL
- No authentication required

**GET /auth/spotify/callback**
- Handles OAuth callback from Spotify
- Exchanges authorization code for access/refresh tokens
- Stores tokens in DynamoDB
- Redirects to frontend with session token

**POST /auth/spotify/refresh**
- Refreshes expired access token
- Requires session token
- Returns new access token

### SoundCloud Authentication (Coming Soon)

**POST /auth/soundcloud/login**
**GET /auth/soundcloud/callback**
**POST /auth/soundcloud/refresh**

## Database Schema

### Users Table (DynamoDB)

```
PK: userId (String)
SK: platform#platformName (String)
---
accessToken: String (encrypted)
refreshToken: String (encrypted)
expiresAt: Number (timestamp)
createdAt: Number (timestamp)
updatedAt: Number (timestamp)
```

## Environment Variables

```bash
# Spotify
SPOTIFY_CLIENT_ID=<your-client-id>
SPOTIFY_CLIENT_SECRET=<your-client-secret>
SPOTIFY_REDIRECT_URI=<your-api-gateway-url>/auth/spotify/callback

# SoundCloud
SOUNDCLOUD_CLIENT_ID=<your-client-id>
SOUNDCLOUD_CLIENT_SECRET=<your-client-secret>
SOUNDCLOUD_REDIRECT_URI=<your-api-gateway-url>/auth/soundcloud/callback

# Database
DYNAMODB_TABLE_NAME=multimusic-tokens
DYNAMODB_REGION=us-east-1

# Frontend
FRONTEND_URL=https://your-frontend-url.com

# Security
JWT_SECRET=<your-jwt-secret>
ENCRYPTION_KEY=<your-encryption-key>
```

## Setup Instructions

### Prerequisites

- AWS Account
- Python 3.13+
- AWS CLI configured
- pip and virtualenv

### Local Development

```bash
# Clone the repository
git clone <your-repo-url>
cd multimusic-platform-backend

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run locally with FastAPI
uvicorn main:app --reload --port 8000
```

### Deployment

**Option 1: AWS SAM (Recommended)**
```bash
# Install SAM CLI
pip install aws-sam-cli

# Build
sam build

# Deploy
sam deploy --guided
```

**Option 2: Serverless Framework**
```bash
# Install Serverless Framework
npm install -g serverless
pip install serverless-python-requirements

# Deploy to AWS
serverless deploy --stage prod
```

**Option 3: Terraform**
```bash
# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply
```

**Option 4: AWS CDK (Python)**
```bash
# Install CDK
pip install aws-cdk-lib

# Deploy
cdk deploy
```

## Project Structure

```
backend/
├── src/
│   ├── handlers/
│   │   ├── spotify.py          # Spotify OAuth handlers
│   │   ├── soundcloud.py       # SoundCloud OAuth handlers
│   │   └── token.py            # Token refresh handlers
│   ├── services/
│   │   ├── oauth.py            # OAuth helper functions
│   │   ├── encryption.py       # Token encryption
│   │   └── dynamodb.py         # Database operations
│   ├── middleware/
│   │   ├── auth.py             # JWT verification
│   │   └── cors.py             # CORS configuration
│   └── utils/
│       ├── logger.py           # Logging utility
│       └── errors.py           # Error handling
├── tests/
│   ├── unit/
│   └── integration/
├── requirements.txt            # Python dependencies
├── template.yaml              # SAM template
├── serverless.yml             # Serverless config (optional)
├── .env.example
└── README.md
```

## Security Considerations

### Token Storage
- All tokens encrypted at rest using AWS KMS
- Refresh tokens stored in DynamoDB with TTL
- Access tokens never logged

### API Security
- CORS restricted to frontend domain
- Rate limiting per user/IP
- JWT tokens for session management
- HTTPS only in production

### Secrets Management
- OAuth secrets stored in AWS Secrets Manager
- Never commit secrets to version control
- Rotate secrets regularly

## Rate Limiting

Lambda functions have minimal rate limiting since they only handle OAuth flows:
- Login endpoint: 10 requests/minute per IP
- Callback endpoint: No limit (single use)
- Refresh endpoint: 20 requests/minute per user

## Monitoring & Logging

**CloudWatch Metrics:**
- Lambda invocation count
- Error rates
- Duration
- DynamoDB read/write capacity

**CloudWatch Logs:**
- All Lambda function logs
- Structured JSON logging
- Error tracking with stack traces

**Alerts:**
- High error rate (>5%)
- Token refresh failures
- DynamoDB throttling

## Cost Estimation

**Monthly costs (assuming 10,000 users):**
- Lambda invocations: ~$0.20
- API Gateway: ~$3.50
- DynamoDB: ~$2.50
- CloudWatch Logs: ~$1.00
- **Total: ~$7-10/month**

Most costs scale linearly with active users.

## Roadmap

- [x] Architecture planning
- [ ] Spotify OAuth implementation
- [ ] DynamoDB setup
- [ ] Token encryption
- [ ] JWT session management
- [ ] SoundCloud OAuth implementation
- [ ] YouTube Music OAuth
- [ ] Token refresh automation
- [ ] Rate limiting
- [ ] Monitoring & alerting
- [ ] CI/CD pipeline
- [ ] Load testing

## Development Workflow

1. **Local testing**: Use AWS SAM Local or run FastAPI directly
2. **Unit tests**: Run `pytest` before commits
3. **Integration tests**: Test against staging environment
4. **Deploy to staging**: `sam deploy --config-env staging`
5. **Manual testing**: Verify OAuth flows work
6. **Deploy to production**: `sam deploy --config-env prod`

## Troubleshooting

### OAuth Callback Fails
- Check redirect URI matches exactly in platform settings
- Verify CORS settings allow frontend domain
- Check CloudWatch logs for detailed errors

### Token Refresh Issues
- Verify refresh token hasn't expired
- Check DynamoDB for token existence
- Ensure OAuth secrets are correct

### High Latency
- Check Lambda cold start times
- Verify DynamoDB provisioned capacity
- Review CloudWatch metrics

## Contributing

1. Create feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass
4. Submit pull request
5. Code review required before merge

## License

[Your chosen license]

## Support

For issues or questions:
- Create an issue in GitHub
- Check CloudWatch logs
- Review API Gateway logs