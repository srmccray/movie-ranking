# Infrastructure Development Guide

This document provides AWS CDK/TypeScript development guidance for the Movie Ranking infrastructure.

> **Important:** Before reading this guide, review the [root CLAUDE.md](../CLAUDE.md) for project-wide conventions. This guide focuses on infrastructure-specific patterns and deployment details.

## Architecture Overview

The application uses a serverless architecture on AWS:

```
                                    CloudFront Distribution
                                           |
                    +----------------------+----------------------+
                    |                                             |
              Default Behavior                              /api/* Behavior
                    |                                             |
              S3 Bucket (OAC)                           HTTP API Gateway
           (Frontend Static Files)                            |
                                                         Lambda Function
                                                       (FastAPI + Mangum)
                                                              |
                                                    PostgreSQL (External)
```

### AWS Services Used

| Service | Purpose | Cost Optimization |
|---------|---------|-------------------|
| **CloudFront** | CDN, HTTPS termination, request routing | Caching for static assets |
| **S3** | Frontend static file hosting | Private bucket via OAC |
| **Lambda** | FastAPI backend via Mangum adapter | ARM64 (20% cheaper), 256MB memory |
| **API Gateway HTTP API** | Lambda trigger | ~70% cheaper than REST API |
| **Route53** | DNS records | - |
| **ACM** | TLS certificate | Free with CloudFront |
| **IAM (OIDC)** | GitHub Actions authentication | No stored credentials |

## Project Structure

```
infra/
  bin/
    infra.ts              # CDK app entry point, stack configuration
  lib/
    movie-ranking-stack.ts # Main stack definition (~370 lines)
  cdk.json                # CDK configuration and feature flags
  package.json            # NPM dependencies
  tsconfig.json           # TypeScript configuration
```

## Key Patterns

### CloudFront Behaviors

The distribution routes requests based on path patterns:

```typescript
// Default behavior - S3 for frontend assets
defaultBehavior: {
  origin: S3BucketOrigin.withOriginAccessControl(bucket, { oac }),
  cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,  // Long cache
}

// API behavior - proxy to Lambda via API Gateway
"/api/*": {
  origin: new HttpOrigin(`${httpApi.httpApiId}.execute-api.${region}.amazonaws.com`),
  cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,  // No cache
  originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
}
```

**Additional API paths proxied to Lambda:**
- `/health` - Health check endpoint
- `/docs` - FastAPI Swagger UI
- `/redoc` - FastAPI ReDoc documentation
- `/openapi.json` - OpenAPI schema

### Origin Access Control (OAC)

The S3 bucket is private and only accessible via CloudFront:

```typescript
// Block all public access
const bucket = new s3.Bucket(this, "FrontendBucket", {
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
});

// CloudFront uses OAC to access bucket
const oac = new cloudfront.S3OriginAccessControl(this, "OAC", {
  signing: cloudfront.Signing.SIGV4_ALWAYS,
});
```

### SPA Routing

Single-page application routing is handled via CloudFront error responses:

```typescript
errorResponses: [
  {
    httpStatus: 404,
    responseHttpStatus: 200,
    responsePagePath: "/index.html",
    ttl: cdk.Duration.minutes(5),
  },
  {
    httpStatus: 403,  // S3 returns 403 for missing objects
    responseHttpStatus: 200,
    responsePagePath: "/index.html",
    ttl: cdk.Duration.minutes(5),
  },
]
```

This allows React Router to handle client-side routing - any path that doesn't match a static file or `/api/*` returns `index.html`.

### GitHub OIDC Authentication

GitHub Actions authenticates using OIDC (OpenID Connect) instead of storing AWS credentials:

```typescript
// Reference existing OIDC provider
const githubOidcProvider = iam.OpenIdConnectProvider.fromOpenIdConnectProviderArn(
  this, "GitHubOidcProvider",
  `arn:aws:iam::${this.account}:oidc-provider/token.actions.githubusercontent.com`
);

// Create role that GitHub Actions can assume
const deployRole = new iam.Role(this, "GitHubActionsDeployRole", {
  assumedBy: new iam.FederatedPrincipal(
    githubOidcProvider.openIdConnectProviderArn,
    {
      StringEquals: { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      StringLike: { "token.actions.githubusercontent.com:sub": `repo:${githubRepo}:*` },
    },
    "sts:AssumeRoleWithWebIdentity"
  ),
});
```

The deploy role has permissions for:
- S3: Upload/delete frontend files
- CloudFront: Create cache invalidations
- Lambda: Update function code and configuration

## Commands

Run these from the `infra/` directory:

```bash
# Install dependencies
npm install

# Compile TypeScript to JavaScript
npm run build

# Synthesize CloudFormation template (preview what will be created)
npm run synth

# Preview changes before deploying
npm run diff

# Deploy stack to AWS
npm run deploy

# Destroy all resources (use with caution!)
npm run destroy
```

### Direct CDK Commands

```bash
# Deploy with verbose output
npx cdk deploy --verbose

# Deploy with approval prompt disabled (CI/CD)
npx cdk deploy --require-approval never

# List all stacks
npx cdk list

# Show CloudFormation template
npx cdk synth > template.yaml
```

## Lambda Environment Variables

The Lambda function requires these environment variables:

| Variable | Description | Set By |
|----------|-------------|--------|
| `DATABASE_URL` | PostgreSQL connection string | Manual (AWS Console/CLI) |
| `SECRET_KEY` | JWT signing key | GitHub Actions |
| `TMDB_API_KEY` | The Movie Database API key | Manual (AWS Console/CLI) |
| `CORS_ORIGIN` | Allowed CORS origin | CDK (automatically set) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | GitHub Actions |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | GitHub Actions |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL | GitHub Actions |

### Initial Setup

After first deployment, manually set secrets via AWS CLI:

```bash
# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name movie-ranking-api \
  --environment "Variables={
    DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname,
    SECRET_KEY=your-secure-secret-key,
    TMDB_API_KEY=your-tmdb-api-key,
    CORS_ORIGIN=https://movies.stephenmccray.com
  }"
```

## Deployment Workflow

The GitHub Actions workflow (`.github/workflows/deploy.yml`) runs on push to `main`:

### 1. Test Phase (Parallel)
- **Backend tests**: Python 3.12, pytest with in-memory SQLite
- **Frontend tests**: Node.js 20, Vitest

### 2. Deploy Phase (After tests pass)

```
1. Configure AWS credentials via OIDC
2. Set up QEMU for ARM64 Docker builds
3. Build frontend (Vite)
4. Upload frontend to S3:
   - Static assets (JS/CSS): max-age=31536000 (1 year)
   - HTML/JSON files: max-age=3600 (1 hour)
5. Package Lambda:
   - Docker build with ARM64 Python 3.12 base image
   - Install requirements.txt
   - Copy app/ and lambda_handler.py
   - Create zip file
6. Deploy Lambda:
   - Update function code
   - Wait for update to complete
   - Update environment variables (secrets)
7. Invalidate CloudFront cache
```

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_DEPLOY_ROLE_ARN` | IAM role ARN for OIDC authentication |
| `S3_BUCKET_NAME` | Frontend bucket name |
| `CLOUDFRONT_DISTRIBUTION_ID` | Distribution ID for invalidation |
| `LAMBDA_FUNCTION_NAME` | Lambda function name |
| `SECRET_KEY` | JWT signing secret |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

## Stack Configuration

Stack props are defined in `bin/infra.ts`:

```typescript
new MovieRankingStack(app, "MovieRankingStack", {
  domainName: "movies.stephenmccray.com",
  hostedZoneId: "ZKW7VVP2HVBFL",
  hostedZoneName: "stephenmccray.com",
  githubRepo: "srmccray/movie-ranking",
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: "us-east-1",  // Required for CloudFront + ACM
  },
});
```

## Important Gotchas

### 1. ACM Certificates Must Be in us-east-1

CloudFront requires ACM certificates to be in `us-east-1`, regardless of where other resources are deployed:

```typescript
env: {
  region: "us-east-1",  // Required - do not change
}
```

### 2. Lambda Environment Placeholders

The CDK defines placeholder environment variables that must be replaced after deployment:

```typescript
environment: {
  DATABASE_URL: "postgresql+asyncpg://user:pass@host:5432/dbname",
  SECRET_KEY: "placeholder-replace-after-deployment",
  TMDB_API_KEY: "placeholder-replace-after-deployment",
}
```

The GitHub Actions workflow updates `SECRET_KEY`, `GOOGLE_*` variables automatically. `DATABASE_URL` and `TMDB_API_KEY` must be set manually.

### 3. CORS Handling

CORS is handled by FastAPI middleware, **not** API Gateway:

```typescript
// API Gateway CORS is disabled
this.httpApi = new apigatewayv2.HttpApi(this, "HttpApi", {
  corsPreflight: undefined,  // Let FastAPI handle CORS
});
```

This allows for consistent CORS behavior between local development and production.

### 4. Lambda Code Exclusions

The Lambda deployment excludes unnecessary files to reduce package size:

```typescript
code: lambda.Code.fromAsset(path.join(__dirname, "../.."), {
  exclude: [
    "frontend/**",
    "infra/**",
    "tests/**",
    "venv/**",
    ".git/**",
    "*.md",
    ".env*",
    // ... more exclusions
  ],
}),
```

### 5. ARM64 Architecture

Lambda uses ARM64 (Graviton2) for cost savings. The GitHub Actions workflow uses QEMU to build compatible packages:

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
  with:
    platforms: arm64

- name: Package Lambda function
  run: |
    docker run --platform linux/arm64 \
      public.ecr.aws/lambda/python:3.12 \
      bash -c "pip install -r requirements.txt ..."
```

### 6. HTTP API vs REST API

The stack uses HTTP API (`apigatewayv2.HttpApi`) which is:
- ~70% cheaper than REST API
- Lower latency
- Simpler (fewer features, but sufficient for this use case)

### 7. CloudFront Cache Invalidation

After deployment, the entire cache is invalidated:

```bash
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

This ensures users get the latest version immediately after deployment.

## Stack Outputs

After deployment, these outputs are available:

| Output | Description |
|--------|-------------|
| `BucketName` | S3 bucket name for frontend files |
| `DistributionId` | CloudFront distribution ID |
| `LambdaFunctionName` | Lambda function name |
| `DeployRoleArn` | IAM role ARN for GitHub Actions |
| `SiteUrl` | Production website URL |
| `HttpApiUrl` | Direct API Gateway URL (bypasses CloudFront) |

View outputs after deployment:

```bash
aws cloudformation describe-stacks \
  --stack-name MovieRankingStack \
  --query 'Stacks[0].Outputs'
```

## Making Infrastructure Changes

### Checklist

- [ ] Review existing patterns in `lib/movie-ranking-stack.ts`
- [ ] Run `npm run diff` to preview changes before deploying
- [ ] Test changes in a separate stack if making significant modifications
- [ ] Update this documentation if adding new resources or patterns
- [ ] Ensure GitHub Actions workflow is updated if new secrets are required
- [ ] Verify IAM permissions are minimal (least privilege)

### Adding a New CloudFront Behavior

```typescript
"/new-path/*": {
  origin: new origins.HttpOrigin(
    `${this.httpApi.httpApiId}.execute-api.${this.region}.amazonaws.com`
  ),
  viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
  cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
  originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
  allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
}
```

### Adding Lambda Environment Variables

1. Add to CDK stack (for documentation/default value):
   ```typescript
   environment: {
     NEW_VAR: "placeholder",
   }
   ```

2. Add to GitHub Actions workflow if it's a secret:
   ```yaml
   --arg new_var "${{ secrets.NEW_VAR }}" \
   '. + { "NEW_VAR": $new_var }'
   ```

3. Add the secret in GitHub repository settings

### Updating Lambda Permissions

Add policies to the Lambda function:

```typescript
this.lambdaFunction.addToRolePolicy(
  new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: ["service:Action"],
    resources: ["arn:aws:service:region:account:resource"],
  })
);
```
