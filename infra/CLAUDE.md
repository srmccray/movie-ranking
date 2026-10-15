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
  cdk.json                # CDK app command, output dir, feature flags
  package.json            # NPM dependencies and scripts
  tsconfig.json           # TypeScript configuration
  .cdk.out/               # Generated: synth output (git-ignored, see below)
```

The CDK app runs through `ts-node` (`"app": "npx ts-node --prefer-ts-exts bin/infra.ts"` in `cdk.json`), so there is no compile step before `synth`, `diff`, or `deploy`.

### CDK Output Directory (`.cdk.out`)

CDK writes its synth output (`manifest.json`, `MovieRankingStack.template.json`, `tree.json`, and staged `asset.*` directories including the Lambda code bundle) to **`infra/.cdk.out/`**, not the CDK default `cdk.out/`. This is set by `"output": ".cdk.out"` in `cdk.json`. The dot-prefix keeps the large generated output out of SpecOps file scanners.

Keep these in sync if you touch any of them:
- `cdk.json`: `"output": ".cdk.out"` (and `.cdk.out` in the `watch.exclude` list)
- `tsconfig.json`: `"outDir": "./.cdk.out"` and `.cdk.out` in `exclude`
- `infra/.gitignore`: `.cdk.out/`

Do not reference `cdk.out/` or `infra/cdk.out/` in commands or scripts; that directory no longer exists. For example, the synthesized template is at `infra/.cdk.out/MovieRankingStack.template.json`. Deleting `.cdk.out` is safe; it is regenerated on the next synth.

## Key Patterns

### CloudFront Behaviors

The distribution routes requests based on path patterns:

```typescript
// Default behavior - S3 for frontend assets
defaultBehavior: {
  origin: origins.S3BucketOrigin.withOriginAccessControl(bucket, { originAccessControl: oac }),
  cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,  // Long cache
}

// API behavior - proxy to Lambda via API Gateway
"/api/*": {
  origin: new origins.HttpOrigin(`${httpApi.httpApiId}.execute-api.${region}.amazonaws.com`),
  cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,  // No cache
  originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
}
```

**Additional API paths proxied to Lambda** (each is its own exact-path behavior, GET/HEAD/OPTIONS only, caching disabled):
- `/health` - Health check endpoint
- `/docs` - FastAPI Swagger UI
- `/redoc` - FastAPI ReDoc documentation
- `/openapi.json` - OpenAPI schema

All behaviors redirect HTTP to HTTPS. `/api/*` allows all methods. The default (S3) behavior allows GET/HEAD/OPTIONS and compresses responses.

### Backend Resources

| Resource | Details |
|----------|---------|
| Lambda (`ApiFunction`) | Name `movie-ranking-api`, Python 3.12, ARM64, 256MB, 30s timeout, handler `lambda_handler.handler` |
| HTTP API (`HttpApi`) | Name `movie-ranking-api`; proxy routes `/{proxy+}` and `/` (ANY method) to the Lambda |
| S3 bucket (`FrontendBucket`) | Name `movies-stephenmccray-com-frontend` (domain with dots replaced by dashes + `-frontend`), S3-managed encryption, `RemovalPolicy.DESTROY` with `autoDeleteObjects` |

`lambda_handler.py` (repo root) wraps the FastAPI app with Mangum using `lifespan="off"`, since Lambda does not support ASGI lifespan events. The `lifespan` startup/shutdown handler in `app/main.py` therefore does not run on Lambda.

The bucket is deleted (with its contents) if the stack is destroyed. The database is external PostgreSQL; the stack creates no RDS or Secrets Manager resources.

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

Note that CloudFront error responses are distribution-wide, not per-behavior: a 403 or 404 returned by the API behaviors (for example `/api/*`) is also rewritten to `200` with `index.html`. Keep this in mind when debugging unexpected HTML responses from the API.

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

The role is named `movie-ranking-deploy` and has permissions for:
- S3: `PutObject`, `DeleteObject`, `ListBucket`, `GetObject` on the frontend bucket
- CloudFront: `CreateInvalidation` on this distribution
- Lambda: `UpdateFunctionCode`, `UpdateFunctionConfiguration`, `GetFunction`, `GetFunctionConfiguration` on the API function

It has **no CloudFormation/CDK permissions**: the GitHub Actions workflow does not run `cdk deploy`. Infrastructure changes are deployed manually (see below).

## CloudWatch Logs Insights

The API emits JSON logs with a `request_id` (also returned in the `X-Request-ID` response header). Find everything for one failing request, or all unhandled errors:

```
fields @timestamp, level, logger, message, request_id, exception_type, status, path
| filter request_id = "<value from X-Request-ID>"
| sort @timestamp asc

fields @timestamp, request_id, exception_type, path
| filter message = "unhandled_exception"
| sort @timestamp desc
```

## Commands

Run these from the `infra/` directory:

```bash
# Install dependencies
npm install

# Type-check / compile TypeScript (emits JS into .cdk.out; not needed for synth/deploy)
npm run build

# Synthesize CloudFormation template (written to infra/.cdk.out/)
npm run synth

# Preview changes before deploying
npm run diff

# Deploy stack to AWS (manual; CI does not do this)
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

# Print the CloudFormation template (YAML) to a file
npx cdk synth > template.yaml
```

Deploying requires local AWS credentials for the target account (`CDK_DEFAULT_ACCOUNT` is read from them) and a CDK-bootstrapped `us-east-1` environment. The synthesized JSON template is also always available at `.cdk.out/MovieRankingStack.template.json` after any `synth`/`diff`/`deploy`.

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

After first deployment, manually set secrets via AWS CLI. Note that `--environment` **replaces the whole variable map**, so include every variable you want to keep (the next CI deploy re-adds `SECRET_KEY` and the `GOOGLE_*` values):

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

The GitHub Actions workflow (`.github/workflows/deploy.yml`) runs on push to `main` (and can be started manually via `workflow_dispatch`). It deploys the **application** (frontend files and Lambda code). It does **not** deploy CDK infrastructure changes and does not run Alembic migrations.

### 1. Test Phase (Parallel)
- **Backend tests**: Python 3.12, `pytest tests/ -v` against in-memory SQLite (`aiosqlite`)
- **Frontend tests**: Node.js 20, `npm run test:run` (Vitest)

### 2. Deploy Phase (After tests pass)

```
1. Configure AWS credentials via OIDC
2. Set up QEMU for ARM64 Docker builds
3. Build frontend (`npx vite build` in frontend/, output frontend/dist)
4. Upload frontend to S3 (two `aws s3 sync` passes):
   - Everything except HTML/JSON, with --delete: max-age=31536000 (1 year)
   - HTML/JSON files: max-age=3600 (1 hour)
5. Package Lambda (does not use the repo Dockerfile):
   - `docker run` of public.ecr.aws/lambda/python:3.12 (linux/arm64)
   - pip install requirements.txt into package/
   - Copy app/ and lambda_handler.py (alembic/ is not included)
   - Zip to lambda.zip
6. Deploy Lambda:
   - update-function-code (--publish)
   - Wait for update to complete
   - Merge secrets into existing environment variables
7. Invalidate CloudFront cache (/*)
```

The code zip built by CI replaces the CDK-bundled code asset; the CDK `code:` asset is only what a manual `cdk deploy` uploads.

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

The GitHub Actions workflow merges `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` into the existing variables automatically (the redirect URI is hardcoded in the workflow as `https://movies.stephenmccray.com/api/v1/auth/google/callback/`). `DATABASE_URL` and `TMDB_API_KEY` must be set manually.

**Warning:** because the CDK stack declares these placeholders, running `cdk deploy` resets the Lambda environment to the placeholder values (dropping `GOOGLE_*` and the real `DATABASE_URL`/`TMDB_API_KEY`). After any manual CDK deploy that touches the function, re-run the GitHub Actions deploy (for `SECRET_KEY`/`GOOGLE_*`) and re-set `DATABASE_URL` and `TMDB_API_KEY`.

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
    // ... also .claude, docs, __pycache__, Dockerfile, docker-compose.yml,
    // pyproject.toml, pytest.ini, alembic.ini, etc.
  ],
}),
```

The asset is staged under `infra/.cdk.out/` during synth. Because `infra/**` is excluded, the output directory is not bundled into the Lambda.

### 5. ARM64 Architecture

Lambda uses ARM64 (Graviton2) for cost savings. The GitHub Actions workflow uses QEMU to build compatible packages:

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
  with:
    platforms: arm64

- name: Package Lambda function
  run: |
    docker run --rm --entrypoint "" \
      -v "$(pwd)":/var/task -v "$(pwd)/package":/opt/package \
      --platform linux/arm64 \
      public.ecr.aws/lambda/python:3.12 \
      bash -c "pip install -r /var/task/requirements.txt -t /opt/package ..."
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
| `DeployRoleArn` | IAM role ARN for GitHub Actions (`movie-ranking-deploy`) |
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
- [ ] Run `npm run diff` to preview changes before deploying (remember `cdk deploy` resets Lambda env vars to placeholders)
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
