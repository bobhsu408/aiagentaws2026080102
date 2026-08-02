/**
 * CareerNav CDK Stack
 *
 * 定義 Agent 部署所需的 AWS 資源：
 * - IAM Role for AgentCore / Lambda（Bedrock + AgentCore Runtime 存取）
 * - Lambda proxy（前端接入用，Function URL 採 AWS_IAM）
 * - S3 bucket（前端靜態網站，私有，符合工作坊規範）
 * - CloudFront（OAC 簽名，對外提供單一公開網址）
 *
 * 為何用 CloudFront + OAC：
 *   比賽沙盒帳號的 guardrail 會封鎖「匿名（AuthType=NONE）」的 Lambda
 *   Function URL（實測匿名呼叫回 403，AWS_IAM 簽名呼叫回 200）。因此改由
 *   CloudFront 以 Origin Access Control 對 Function URL 做 SigV4 簽名，
 *   前端只需打同源相對路徑，不必自行簽名或引入 Cognito。
 *
 *   S3 亦依工作坊規範改為完全私有（Block Public Access 全開），僅透過
 *   CloudFront OAC 讀取，不開任何公開存取。
 *
 * 注意：AgentCore Runtime 本身由 `agentcore deploy` CLI 管理，
 * 不屬於此 Stack；Lambda 以硬編碼 ARN 呼叫它。
 */
import * as cdk from "aws-cdk-lib";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export class CareerNavStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ========================================
    // IAM Role: Lambda proxy 執行角色
    // ========================================
    const agentRole = new iam.Role(this, "AgentCoreRole", {
      roleName: "careernav-agentcore-role",
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("bedrock.amazonaws.com"),
        new iam.ServicePrincipal("lambda.amazonaws.com"),
      ),
      description: "Role for CareerNav proxy Lambda to access Bedrock / AgentCore",
    });

    // Bedrock model invocation
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ],
        resources: [`arn:aws:bedrock:${this.region}::foundation-model/*`],
      })
    );

    // AgentCore memory / agent（保留既有權限）
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

    // AgentCore Runtime invocation（Lambda proxy 呼叫 Runtime）
    agentRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock-agentcore:InvokeAgentRuntime"],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:runtime/*`,
        ],
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
    // AGENT_RUNTIME_ARN：對應 agentcore/agentcore.json 部署出的 Runtime
    // （見 docs/DEPLOY_NOTES.md），手動填入而非 CDK cross-stack 參照，
    // 因為 AgentCore Runtime 由獨立的 `agentcore deploy` CLI 管理。
    const proxyLambda = new lambda.Function(this, "ChatProxy", {
      functionName: "careernav-chat-proxy",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "proxy.handler",
      code: lambda.Code.fromAsset("../lambda"),
      timeout: cdk.Duration.seconds(90),
      memorySize: 256,
      environment: {
        AGENT_RUNTIME_ARN:
          "arn:aws:bedrock-agentcore:us-west-2:881768789243:runtime/careernav_careernav-Su5fjSE2LM",
        AWS_REGION_NAME: this.region,
      },
      role: agentRole,
    });

    // Function URL：採 AWS_IAM（沙盒 guardrail 會擋匿名 NONE）。
    // 由 CloudFront OAC 簽名呼叫，不對外直接暴露。
    const fnUrl = proxyLambda.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.AWS_IAM,
    });

    // ========================================
    // S3: 前端靜態網站（完全私有，僅 CloudFront OAC 可讀）
    // ========================================
    const frontendBucket = new s3.Bucket(this, "FrontendBucket", {
      bucketName: `careernav-frontend-${this.account}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // ========================================
    // CloudFront：單一公開網址，兩個 origin
    //   /*     → S3（前端靜態檔，OAC 讀取）
    //   /chat  → Lambda Function URL（OAC 簽名呼叫）
    // ========================================
    const s3Origin = origins.S3BucketOrigin.withOriginAccessControl(frontendBucket);

    // readTimeout 拉到 60 秒（免申請配額的上限；預設僅 30 秒）。
    // 實測：一般對話輪次約 11~14 秒，但「一次問到底」觸發完整六步驟工具鏈
    // 的請求可達 59 秒，用預設 30 秒會逾時，且 CloudFront 會對 GET 重試，
    // 重試打進同一個 session 會拿到空回應。
    // connectionAttempts=1：關掉連線重試，避免重複觸發同一輪 Agent 推理。
    const fnOrigin = origins.FunctionUrlOrigin.withOriginAccessControl(fnUrl, {
      readTimeout: cdk.Duration.seconds(60),
      keepaliveTimeout: cdk.Duration.seconds(60),
      connectionAttempts: 1,
    });

    // /chat 採 GET + query string（q、session_id），不用 POST。
    // 原因：OAC 對 POST/PUT 要求呼叫端自行計算 body 的 SHA256 並帶
    // x-amz-content-sha256 header（Lambda 不接受 unsigned payload）；
    // 改用 GET 沒有 body，CloudFront 可獨立完成 SigV4 簽名，前端零簽名邏輯。
    //
    // 必須把 query string 轉發到 origin，否則 Lambda 收不到 q 參數。
    // 同時不可轉發 viewer 的 Authorization / Host header，會與 OAC 簽名衝突。
    const chatOriginRequestPolicy = new cloudfront.OriginRequestPolicy(
      this,
      "ChatOriginRequestPolicy",
      {
        originRequestPolicyName: "careernav-chat-orp",
        headerBehavior: cloudfront.OriginRequestHeaderBehavior.none(),
        queryStringBehavior: cloudfront.OriginRequestQueryStringBehavior.all(),
        cookieBehavior: cloudfront.OriginRequestCookieBehavior.none(),
      }
    );

    const distribution = new cloudfront.Distribution(this, "Distribution", {
      comment: "CareerNav 職涯導航家 — 前端 + Chat API",
      defaultRootObject: "index.html",
      defaultBehavior: {
        origin: s3Origin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      additionalBehaviors: {
        "/chat": {
          origin: fnOrigin,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: chatOriginRequestPolicy,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        },
      },
    });

    // CloudFront OAC 呼叫 Lambda Function URL 需要「兩條」權限：
    //   1. lambda:InvokeFunctionUrl — CDK 的 FunctionUrlOrigin
    //      .withOriginAccessControl() 會自動加
    //   2. lambda:InvokeFunction    — CDK 不會自動加，必須手動補
    // 缺第 2 條時 CloudFront 呼叫會回 403 Forbidden（已實測確認）。
    // 依據 AWS 文件 private-content-restricting-access-to-lambda 的
    // 「Grant CloudFront permission to access the Lambda function URL」段落，
    // 該處明確列出兩道 add-permission 指令。
    proxyLambda.addPermission("AllowCloudFrontInvokeFunction", {
      principal: new iam.ServicePrincipal("cloudfront.amazonaws.com"),
      action: "lambda:InvokeFunction",
      sourceArn: `arn:aws:cloudfront::${this.account}:distribution/${distribution.distributionId}`,
    });

    // ========================================
    // Outputs
    // ========================================
    new cdk.CfnOutput(this, "DemoUrl", {
      value: `https://${distribution.distributionDomainName}`,
      description: "公開 Demo 網址（CloudFront）— 填入前端無需，直接開此網址即可",
    });

    new cdk.CfnOutput(this, "FrontendBucketName", {
      value: frontendBucket.bucketName,
      description: "前端 S3 bucket 名稱（部署後上傳 index.html 到此）",
    });

    new cdk.CfnOutput(this, "AgentRoleArn", {
      value: agentRole.roleArn,
      description: "Proxy Lambda IAM Role ARN",
    });
  }
}
