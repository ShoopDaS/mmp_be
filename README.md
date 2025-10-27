# MultiMusic Platform - Backend

Backend services for the MultiMusic Platform, handling OAuth authentication flows and token management for multiple streaming services.

## Overview

The backend is intentionally minimal, consisting of serverless Lambda functions that handle OAuth callbacks and token refresh operations. The architecture keeps API requests client-side to avoid rate limiting and improve performance.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CloudFront + WAF                     │
│                 (Public Internet)                       │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS (Only entry point)
                         ▼
                  ┌──────────────┐
                  │ VPC Endpoint │
                  │ (API Gateway)│
                  └──────┬───────┘
                         │
        ┌────────────────┴────────────────┐
        │            VPC                  │
        │  Private Subnets (No Internet)  │
        │                                 │
        │  ┌──────────────┐               │
        │  │ API Gateway  │               │
        │  │  (Private)   │               │
        │  └──────┬───────┘               │
        │         │                       │
        │         ▼                       │
        │  ┌──────────────┐               │
        │  │   Lambda     │───────NAT─────┼──▶ Spotify API
        │  │  Functions   │    Gateway    │    SoundCloud API
        │  └──────┬───────┘               │
        │         │                       │
        │         ▼                       │
        │  VPC Endpoints (Private):      │
        │  ┌──────────────┐              │
        │  │  DynamoDB    │              │
        │  │  Secrets Mgr │              │
        │  │  CloudWatch  │              │
        │  └──────────────┘              │
        └─────────────────────────────────┘

Frontend (Browser)
      │
      │ Direct API calls with user token
      ▼
┌─────────────┐
│   Spotify   │
│ SoundCloud  │
│     APIs    │
└─────────────┘
```

**Key Principle**: The backend only handles authentication. All music-related API calls (search, playback, playlists) go directly from the frontend to the streaming service APIs using the user's access token.

**Security Model**: Private API Gateway accessible ONLY through CloudFront + WAF. Network-level isolation ensures no direct internet access to API Gateway.

## Why This Approach?

- **No rate limiting issues**: Each user uses their own API quota
- **Better performance**: No backend proxy bottleneck
- **Lower costs**: Minimal Lambda invocations (only for OAuth)
- **Scalability**: Frontend scales infinitely via CDN
- **Security**: Private API Gateway + CloudFront + WAF provides enterprise-grade protection
- **Network Isolation**: API Gateway physically inaccessible from internet, only accessible through VPC endpoint

## Tech Stack

## Tech Stack

**Primary Stack:**
- Python 3.13
- FastAPI (for local development)
- AWS Lambda (Python runtime)
- API Gateway (Private - VPC endpoint only)
- CloudFront + WAF (DDoS protection, rate limiting)
- VPC (Private subnets, NAT Gateway)
- DynamoDB (token storage via VPC endpoint)
- AWS Secrets Manager (OAuth secrets via VPC endpoint)
- Boto3 (AWS SDK)

**Infrastructure:**
- VPC with private subnets (10.0.0.0/16)
- NAT Gateway (for Lambda to call external OAuth APIs)
- VPC Endpoints:
  - API Gateway (Interface endpoint)
  - DynamoDB (Gateway endpoint - free)
  - Secrets Manager (Interface endpoint)
  - CloudWatch Logs (Interface endpoint)
- CloudFront Distribution (single entry point)
- AWS WAF Web ACL (DDoS, rate limiting, bot protection)

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

**Using Terraform (Recommended for this project)**

The infrastructure will be written in Terraform, including:
- VPC with private subnets and NAT Gateway
- VPC Endpoints (API Gateway, DynamoDB, Secrets Manager, CloudWatch)
- Private API Gateway with resource policy
- Lambda functions with VPC configuration
- CloudFront distribution with WAF
- DynamoDB tables
- IAM roles and policies
- Security groups

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Destroy (when needed)
terraform destroy
```

**Alternative: AWS SAM**
```bash
# Install SAM CLI
pip install aws-sam-cli

# Build
sam build

# Deploy
sam deploy --guided
```

**Alternative: AWS CDK (Python)**
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
├── template.yaml              # SAM template (optional)
├── serverless.yml             # Serverless config (optional)
├── .env.example
└── README.md
```

## Security Considerations

### Network Security
- **Private API Gateway**: Only accessible via VPC endpoint, no public internet access
- **CloudFront as sole entry point**: All traffic must go through CloudFront + WAF
- **VPC isolation**: Lambda functions in private subnets with no direct internet access
- **NAT Gateway**: Controlled outbound access for OAuth API calls only

### Application Security
- All tokens encrypted at rest using AWS KMS
- Refresh tokens stored in DynamoDB with TTL
- Access tokens never logged
- JWT tokens for session management
- OAuth secrets stored in AWS Secrets Manager
- Never commit secrets to version control
- Rotate secrets regularly

### WAF Protection
- **Rate Limiting**: 100 requests per 5 minutes per IP
- **AWS Managed Rules**:
  - Core Rule Set (OWASP Top 10)
  - Known Bad Inputs
  - IP Reputation Lists
- **DDoS Protection**: Automatic mitigation via CloudFront + WAF
- **Bot Detection**: AWS Managed Bot Control

### API Security
- CORS restricted to frontend domain
- Rate limiting per user/IP
- HTTPS only in production
- Request validation at API Gateway
- Lambda function isolation via IAM roles

## Rate Limiting

Lambda functions have minimal rate limiting since they only handle OAuth flows:
- Login endpoint: 10 requests/minute per IP
- Callback endpoint: No limit (single use)
- Refresh endpoint: 20 requests/minute per user

## Monitoring & Logging

**CloudWatch Metrics:**
- Lambda invocation count and errors
- API Gateway 4xx/5xx errors
- DynamoDB read/write capacity and throttling
- NAT Gateway bytes processed
- VPC Endpoint connections

**CloudWatch Logs:**
- Lambda function logs (structured JSON)
- API Gateway access logs
- WAF logs (sampled to control costs)

**CloudWatch Alarms:**
- High WAF block rate (> 10% of requests)
- API Gateway error rate (> 5%)
- Lambda errors or timeouts
- DynamoDB throttling events
- High latency (> 1 second p99)
- NAT Gateway connection errors

**AWS WAF Monitoring:**
- Blocked requests by rule
- Top blocked IPs
- Request patterns and anomalies
- Bot detection metrics

## Cost Estimation

**Monthly costs for 10,000 active users:**

**Networking:**
- NAT Gateway: ~$32.00 (required for Lambda to call Spotify/SoundCloud OAuth APIs)
- NAT Data Transfer: ~$4.50
- VPC Endpoints (Interface): ~$7.20/month (API Gateway, Secrets, CloudWatch)
- VPC Endpoint (Gateway): $0.00 (DynamoDB - free)

**CDN & Security:**
- CloudFront Requests: ~$0.50
- CloudFront Data Transfer: ~$1.00
- AWS WAF Web ACL: ~$5.00
- WAF Rules (3 custom): ~$3.00
- WAF Request Charges: ~$1.00

**Compute & Storage:**
- Lambda Invocations: ~$0.20
- Lambda Duration: ~$0.50
- API Gateway Requests: ~$3.50
- DynamoDB (on-demand): ~$2.50
- Secrets Manager: ~$0.40

**Total: ~$61/month for 10,000 users**

**Cost Breakdown:**
- ~70% networking (NAT Gateway + VPC Endpoints)
- ~15% security (WAF)
- ~15% compute & storage

**Note:** Most costs scale linearly with active users. NAT Gateway is a fixed cost regardless of traffic volume.

**Cost Optimization Option:**
Split Lambda functions to avoid NAT Gateway:
- OAuth functions outside VPC (call Spotify/SoundCloud): ~$0.20/mo
- User management functions in VPC (DynamoDB only): ~$0.30/mo
- **Savings:** ~$37/month
- **Trade-off:** Slightly more complex architecture

## Roadmap

- [x] Architecture planning
- [x] Security design (Private API Gateway + CloudFront + WAF)
- [ ] Terraform infrastructure code
  - [ ] VPC and networking
  - [ ] Private API Gateway with VPC endpoint
  - [ ] CloudFront + WAF configuration
  - [ ] Lambda functions with VPC config
  - [ ] DynamoDB tables
  - [ ] IAM roles and policies
- [ ] Python application code
  - [ ] Spotify OAuth implementation
  - [ ] Token encryption utilities
  - [ ] DynamoDB operations
  - [ ] JWT session management
- [ ] SoundCloud OAuth implementation
- [ ] YouTube Music OAuth
- [ ] Token refresh automation
- [ ] Monitoring & alerting setup
- [ ] CI/CD pipeline
- [ ] Load testing
- [ ] Documentation

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