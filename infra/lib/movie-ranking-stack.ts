import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as targets from "aws-cdk-lib/aws-route53-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigatewayv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as apigatewayv2Integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import { Construct } from "constructs";
import * as path from "path";

interface MovieRankingStackProps extends cdk.StackProps {
  domainName: string;
  hostedZoneId: string;
  hostedZoneName: string;
  githubRepo: string;
}

export class MovieRankingStack extends cdk.Stack {
  public readonly bucket: s3.Bucket;
  public readonly distribution: cloudfront.Distribution;
  public readonly lambdaFunction: lambda.Function;
  public readonly httpApi: apigatewayv2.HttpApi;

  constructor(scope: Construct, id: string, props: MovieRankingStackProps) {
    super(scope, id, props);

    const { domainName, hostedZoneId, hostedZoneName, githubRepo } = props;

    // ==========================================================================
    // Route53 Hosted Zone (existing)
    // ==========================================================================
    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(
      this,
      "HostedZone",
      {
        hostedZoneId,
        zoneName: hostedZoneName,
      }
    );

    // ==========================================================================
    // ACM Certificate for HTTPS
    // Must be in us-east-1 for CloudFront
    // ==========================================================================
    const certificate = new acm.Certificate(this, "SiteCertificate", {
      domainName,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    // ==========================================================================
    // S3 Bucket for Frontend Static Files
    // Private bucket - only accessible via CloudFront OAC
    // ==========================================================================
    this.bucket = new s3.Bucket(this, "FrontendBucket", {
      bucketName: `${domainName.replace(/\./g, "-")}-frontend`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // ==========================================================================
    // Lambda Function for FastAPI Backend
    // Cost-optimized: 256MB memory, 30s timeout
    // ==========================================================================
    this.lambdaFunction = new lambda.Function(this, "ApiFunction", {
      functionName: "movie-ranking-api",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "lambda_handler.handler",
      // Code is deployed from the project root, excluding unnecessary files
      code: lambda.Code.fromAsset(path.join(__dirname, "../.."), {
        exclude: [
          "frontend",
          "frontend/**",
          "infra",
          "infra/**",
          "venv",
          "venv/**",
          "tests",
          "tests/**",
          ".git",
          ".git/**",
          "*.md",
          ".env*",
          ".pytest_cache",
          ".pytest_cache/**",
          "__pycache__",
          "**/__pycache__",
          "*.pyc",
          ".claude",
          ".claude/**",
          "docs",
          "docs/**",
          ".gitignore",
          ".dockerignore",
          "docker-compose.yml",
          "Dockerfile",
          "pyproject.toml",
          "pytest.ini",
          "alembic.ini",
        ],
      }),
      memorySize: 256, // Cost-optimized: minimal memory for API workload
      timeout: cdk.Duration.seconds(30),
      architecture: lambda.Architecture.ARM_64, // Cost savings: ~20% cheaper than x86
      environment: {
        // Placeholder values - set actual values after deployment via AWS Console or CLI
        DATABASE_URL: "postgresql+asyncpg://user:pass@host:5432/dbname",
        SECRET_KEY: "placeholder-replace-after-deployment",
        TMDB_API_KEY: "placeholder-replace-after-deployment",
        CORS_ORIGIN: `https://${domainName}`,
      },
      description: "Movie Ranking API - FastAPI backend via Mangum",
    });

    // ==========================================================================
    // API Gateway HTTP API
    // Cost-optimized: HTTP API is ~70% cheaper than REST API
    // ==========================================================================
    this.httpApi = new apigatewayv2.HttpApi(this, "HttpApi", {
      apiName: "movie-ranking-api",
      description: "HTTP API for Movie Ranking backend",
      // CORS is handled by FastAPI middleware
      corsPreflight: undefined,
    });

    // Lambda integration for HTTP API
    const lambdaIntegration =
      new apigatewayv2Integrations.HttpLambdaIntegration(
        "LambdaIntegration",
        this.lambdaFunction
      );

    // Route all requests to Lambda (proxy integration)
    // Matches: /api/*, /health, /docs, /redoc, /openapi.json
    this.httpApi.addRoutes({
      path: "/{proxy+}",
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: lambdaIntegration,
    });

    // Also add root route
    this.httpApi.addRoutes({
      path: "/",
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: lambdaIntegration,
    });

    // ==========================================================================
    // CloudFront Origin Access Control for S3
    // ==========================================================================
    const oac = new cloudfront.S3OriginAccessControl(this, "OAC", {
      signing: cloudfront.Signing.SIGV4_ALWAYS,
    });

    // ==========================================================================
    // CloudFront Distribution
    // - Default behavior: S3 static files
    // - /api/* behavior: API Gateway
    // - SPA routing: 404/403 -> /index.html
    // ==========================================================================
    this.distribution = new cloudfront.Distribution(this, "Distribution", {
      // Default behavior - S3 static files for frontend
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(this.bucket, {
          originAccessControl: oac,
        }),
        viewerProtocolPolicy:
          cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
      },
      // API behavior - proxy to API Gateway
      additionalBehaviors: {
        "/api/*": {
          origin: new origins.HttpOrigin(
            `${this.httpApi.httpApiId}.execute-api.${this.region}.amazonaws.com`
          ),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          // Don't cache API responses by default
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          // Forward all headers for API requests
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        },
        // Also proxy health, docs, and OpenAPI endpoints
        "/health": {
          origin: new origins.HttpOrigin(
            `${this.httpApi.httpApiId}.execute-api.${this.region}.amazonaws.com`
          ),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        },
        "/docs": {
          origin: new origins.HttpOrigin(
            `${this.httpApi.httpApiId}.execute-api.${this.region}.amazonaws.com`
          ),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        },
        "/redoc": {
          origin: new origins.HttpOrigin(
            `${this.httpApi.httpApiId}.execute-api.${this.region}.amazonaws.com`
          ),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        },
        "/openapi.json": {
          origin: new origins.HttpOrigin(
            `${this.httpApi.httpApiId}.execute-api.${this.region}.amazonaws.com`
          ),
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        },
      },
      domainNames: [domainName],
      certificate,
      defaultRootObject: "index.html",
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      // SPA routing: redirect 404/403 to index.html for client-side routing
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.minutes(5),
        },
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
          ttl: cdk.Duration.minutes(5),
        },
      ],
    });

    // ==========================================================================
    // Route53 A Record
    // Point movies.stephenmccray.com to CloudFront
    // ==========================================================================
    new route53.ARecord(this, "SiteARecord", {
      zone: hostedZone,
      recordName: domainName,
      target: route53.RecordTarget.fromAlias(
        new targets.CloudFrontTarget(this.distribution)
      ),
    });

    // ==========================================================================
    // GitHub Actions OIDC Provider and Deploy Role
    // Allows GitHub Actions to deploy without storing AWS credentials
    // Uses existing OIDC provider (created by personal-website stack)
    // ==========================================================================
    const githubOidcProviderArn = `arn:aws:iam::${this.account}:oidc-provider/token.actions.githubusercontent.com`;

    const deployRole = new iam.Role(this, "GitHubActionsDeployRole", {
      roleName: "movie-ranking-deploy",
      assumedBy: new iam.FederatedPrincipal(
        githubOidcProviderArn,
        {
          StringEquals: {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          },
          StringLike: {
            "token.actions.githubusercontent.com:sub": `repo:${githubRepo}:*`,
          },
        },
        "sts:AssumeRoleWithWebIdentity"
      ),
      description: "IAM role for GitHub Actions deployment of movie-ranking",
    });

    // S3 permissions for frontend deployment
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObject",
        ],
        resources: [this.bucket.bucketArn, `${this.bucket.bucketArn}/*`],
      })
    );

    // CloudFront invalidation permission
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["cloudfront:CreateInvalidation"],
        resources: [
          `arn:aws:cloudfront::${this.account}:distribution/${this.distribution.distributionId}`,
        ],
      })
    );

    // Lambda update permission for backend deployment
    deployRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "lambda:UpdateFunctionCode",
          "lambda:GetFunction",
          "lambda:UpdateFunctionConfiguration",
        ],
        resources: [this.lambdaFunction.functionArn],
      })
    );

    // ==========================================================================
    // Stack Outputs
    // ==========================================================================
    new cdk.CfnOutput(this, "BucketName", {
      value: this.bucket.bucketName,
      description: "S3 bucket name for frontend static files",
    });

    new cdk.CfnOutput(this, "DistributionId", {
      value: this.distribution.distributionId,
      description: "CloudFront distribution ID",
    });

    new cdk.CfnOutput(this, "LambdaFunctionName", {
      value: this.lambdaFunction.functionName,
      description: "Lambda function name for API backend",
    });

    new cdk.CfnOutput(this, "DeployRoleArn", {
      value: deployRole.roleArn,
      description: "IAM role ARN for GitHub Actions deployment",
    });

    new cdk.CfnOutput(this, "SiteUrl", {
      value: `https://${domainName}`,
      description: "Website URL",
    });

    new cdk.CfnOutput(this, "HttpApiUrl", {
      value: this.httpApi.apiEndpoint,
      description: "HTTP API Gateway URL (direct, bypassing CloudFront)",
    });
  }
}
