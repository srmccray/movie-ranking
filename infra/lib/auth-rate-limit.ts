import * as wafv2 from "aws-cdk-lib/aws-wafv2";
import { Construct } from "constructs";

/** Requests per IP per evaluation window before the rule triggers. */
export const AUTH_RATE_LIMIT = 100;
/** Evaluation window in seconds (AWS default, stated explicitly). */
export const AUTH_RATE_WINDOW_SEC = 300;

interface AuthRateLimitProps {
  /**
   * "count" only records matches in the AuthRateLimit metric; "block" returns
   * 403 at the edge. Start in count, review the metric for a week, then block
   * (TASK-0036). Overridable with `-c authRateLimitAction=block`.
   */
  action: "count" | "block";
}

/**
 * CloudFront-scope WAF web ACL with a per-IP rate rule on /api/v1/auth/*.
 * CLOUDFRONT-scope WAF resources must live in us-east-1 (the stack's region).
 */
export class AuthRateLimit extends Construct {
  public readonly webAcl: wafv2.CfnWebACL;

  constructor(scope: Construct, id: string, props: AuthRateLimitProps) {
    super(scope, id);

    this.webAcl = new wafv2.CfnWebACL(this, "WebAcl", {
      name: "movie-ranking-web-acl",
      scope: "CLOUDFRONT",
      defaultAction: { allow: {} },
      visibilityConfig: {
        cloudWatchMetricsEnabled: true,
        metricName: "MovieRankingWebAcl",
        sampledRequestsEnabled: true,
      },
      rules: [
        {
          name: "AuthRateLimit",
          priority: 0,
          action: props.action === "block" ? { block: {} } : { count: {} },
          statement: {
            rateBasedStatement: {
              limit: AUTH_RATE_LIMIT,
              evaluationWindowSec: AUTH_RATE_WINDOW_SEC,
              aggregateKeyType: "IP",
              scopeDownStatement: {
                byteMatchStatement: {
                  searchString: "/api/v1/auth/",
                  fieldToMatch: { uriPath: {} },
                  positionalConstraint: "STARTS_WITH",
                  textTransformations: [{ priority: 0, type: "NONE" }],
                },
              },
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: "AuthRateLimit",
            sampledRequestsEnabled: true,
          },
        },
      ],
    });
  }
}
