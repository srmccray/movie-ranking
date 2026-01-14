#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { MovieRankingStack } from "../lib/movie-ranking-stack";

const app = new cdk.App();

new MovieRankingStack(app, "MovieRankingStack", {
  domainName: "movies.stephenmccray.com",
  hostedZoneId: "ZKW7VVP2HVBFL",
  hostedZoneName: "stephenmccray.com",
  githubRepo: "srmccray/movie-ranking",
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: "us-east-1", // Required for CloudFront + ACM
  },
});
