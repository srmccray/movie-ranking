import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigatewayv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import { Construct } from "constructs";

interface ApiMonitoringProps {
  lambdaFunction: lambda.Function;
  httpApi: apigatewayv2.HttpApi;
  /** Email for alarm notifications (CDK context `alertEmail`); never committed. */
  alertEmail?: string;
}

/**
 * SNS topic plus four CloudWatch alarms for the API (TASK-0039).
 * Thresholds are starting points; tune after a week of data.
 */
export class ApiMonitoring extends Construct {
  public readonly topic: sns.Topic;

  constructor(scope: Construct, id: string, props: ApiMonitoringProps) {
    super(scope, id);
    const { lambdaFunction, httpApi, alertEmail } = props;

    this.topic = new sns.Topic(this, "AlarmTopic", {
      topicName: "movie-ranking-alarms",
    });
    if (alertEmail) {
      this.topic.addSubscription(new subscriptions.EmailSubscription(alertEmail));
    }
    const action = new cloudwatchActions.SnsAction(this.topic);
    const fiveMinutes = cdk.Duration.minutes(5);
    const atLeast = cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD;
    const notBreaching = cloudwatch.TreatMissingData.NOT_BREACHING;

    const alarms: cloudwatch.Alarm[] = [
      new cloudwatch.Alarm(this, "LambdaErrorsAlarm", {
        alarmName: "movie-ranking-lambda-errors",
        alarmDescription: "Lambda invocation errors >= 1 in 5 minutes",
        metric: lambdaFunction.metricErrors({ period: fiveMinutes, statistic: "Sum" }),
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator: atLeast,
        treatMissingData: notBreaching,
      }),
      new cloudwatch.Alarm(this, "LambdaThrottlesAlarm", {
        alarmName: "movie-ranking-lambda-throttles",
        alarmDescription: "Lambda throttles >= 1 in 5 minutes",
        metric: lambdaFunction.metricThrottles({ period: fiveMinutes, statistic: "Sum" }),
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator: atLeast,
        treatMissingData: notBreaching,
      }),
      new cloudwatch.Alarm(this, "LambdaDurationP95Alarm", {
        alarmName: "movie-ranking-lambda-duration-p95",
        alarmDescription: "Lambda p95 duration above 20s (timeout is 30s)",
        metric: lambdaFunction.metricDuration({ period: fiveMinutes, statistic: "p95" }),
        threshold: 20_000, // milliseconds
        evaluationPeriods: 1,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: notBreaching,
      }),
      new cloudwatch.Alarm(this, "ApiGateway5xxAlarm", {
        alarmName: "movie-ranking-api-5xx",
        alarmDescription: "HTTP API 5xx responses >= 5 in 5 minutes",
        metric: httpApi.metricServerError({ period: fiveMinutes, statistic: "Sum" }),
        threshold: 5,
        evaluationPeriods: 1,
        comparisonOperator: atLeast,
        treatMissingData: notBreaching,
      }),
    ];
    alarms.forEach((alarm) => alarm.addAlarmAction(action));
  }
}
