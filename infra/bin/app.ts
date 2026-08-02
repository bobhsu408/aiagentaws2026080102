#!/usr/bin/env node
/**
 * CDK App 進入點
 *
 * 定義要部署的 Stack。比賽當天拿到新帳號後，
 * 修改 env 的 account/region 即可重新部署。
 */
import * as cdk from "aws-cdk-lib";
import { CareerNavStack } from "../lib/stack";

const app = new cdk.App();

new CareerNavStack(app, "CareerNavStack", {
  env: {
    region: process.env.AWS_REGION || "us-west-2",
    // account 由 CLI profile 自動帶入
  },
  description: "CareerNav Agent Infrastructure — 職涯導航家",
});
