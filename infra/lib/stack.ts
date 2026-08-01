/**
 * CareerNav CDK Stack
 *
 * 定義 Agent 部署所需的 AWS 資源：
 * - IAM Role for AgentCore（Bedrock 存取）
 * - Lambda proxy（前端接入用）
 * - S3 bucket（前端靜態網站）
 *
 * 注意：AgentCore 本身由 `agentcore deploy` CLI 管理，
 * 此 Stack 只負責周邊基礎設施。
 */
import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export class CareerNavStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ========================================
    // IAM Role: AgentCore 執行角色
    // ========================================
    const agentRole = new iam.Role(this, "AgentCoreRole", {
      roleName: "careernav-agentcore-role",
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("bedrock.amazonaws.com"),
        new iam.ServicePrincipal("lambda.amazonaws.com"),
      ),
      description: "Role for CareerNav AgentCore to access Bedrock models",
    });

    // Bedrock model invocation
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ],
        resources: [
          `arn:aws:bedrock:${this.region}::foundation-model/*`,
        ],
      })
    );

    // AgentCore memory (if needed)
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:*AgentMemory*",
          "bedrock:GetAgent*",
          "bedrock:InvokeAgent",
        ],
        resources: ["*"],
      })
    );

    // CloudWatch Logs
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ],
        resources: ["*"],
      })
    );

    // ========================================
    // Lambda: Chat Proxy
    // ========================================
    const proxyLambda = new lambda.Function(this, "ChatProxy", {
      functionName: "careernav-chat-proxy",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "proxy.handler",
      code: lambda.Code.fromAsset("../lambda"),
      timeout: cdk.Duration.seconds(90),
      memorySize: 256,
      environment: {
        AGENT_ID: "", // 部署 AgentCore 後填入
        AGENT_ALIAS_ID: "", // 部署 AgentCore 後填入
        AWS_REGION_NAME: this.region,
      },
      role: agentRole,
    });

    // Lambda Function URL (無 auth，demo 用)
    const fnUrl = proxyLambda.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedOrigins: ["*"],
        allowedMethods: [lambda.HttpMethod.POST, lambda.HttpMethod.OPTIONS],
        allowedHeaders: ["content-type"],
      },
    });

    // ========================================
    // S3: 前端靜態網站
    // ========================================
    const frontendBucket = new s3.Bucket(this, "FrontendBucket", {
      bucketName: `careernav-frontend-${this.account}`,
      websiteIndexDocument: "index.html",
      publicReadAccess: true,
      blockPublicAccess: new s3.BlockPublicAccess({
        blockPublicAcls: false,
        ignorePublicAcls: false,
        blockPublicPolicy: false,
        restrictPublicBuckets: false,
      }),
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // ========================================
    // Outputs
    // ========================================
    new cdk.CfnOutput(this, "ProxyLambdaUrl", {
      value: fnUrl.url,
      description: "Chat proxy Lambda Function URL",
    });

    new cdk.CfnOutput(this, "FrontendBucketUrl", {
      value: frontendBucket.bucketWebsiteUrl,
      description: "Frontend S3 website URL",
    });

    new cdk.CfnOutput(this, "AgentRoleArn", {
      value: agentRole.roleArn,
      description: "AgentCore IAM Role ARN",
    });
  }
}
