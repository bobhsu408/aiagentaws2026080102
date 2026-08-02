/**
 * 前端本機預覽用靜態檔案伺服器（零依賴，只用 Node 內建模組）。
 *
 * 用途：在本機預覽 frontend/ 下的畫面（index.html、community.html）。
 * 為什麼不直接開 file://：SpeechRecognition（語音輸入）要求安全來源，
 * file:// 會被瀏覽器擋掉；localhost 屬安全來源，語音功能才試得出來。
 *
 * 用法：
 *   node scripts/preview_frontend.js            # 預設 http://127.0.0.1:5173
 *   node scripts/preview_frontend.js 8080       # 指定埠號
 *
 * 注意：僅綁定 127.0.0.1（不對外網開放），且只讀取 frontend/ 目錄內的檔案。
 * 這是本機開發工具，不是部署用的伺服器。
 */

"use strict";

const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const HOST = "127.0.0.1";
const DEFAULT_PORT = 5173;
const ROOT = path.resolve(__dirname, "..", "frontend");

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

/**
 * 把請求路徑解析成 frontend/ 底下的實體檔案路徑。
 * 回傳 null 表示路徑越出 ROOT（防止 ../ 目錄穿越）。
 */
function resolveRequestPath(requestUrl) {
  const { pathname } = new URL(requestUrl, `http://${HOST}`);
  const decoded = decodeURIComponent(pathname);
  const relative = decoded === "/" ? "index.html" : decoded.replace(/^\/+/, "");
  const resolved = path.resolve(ROOT, relative);

  if (resolved !== ROOT && !resolved.startsWith(ROOT + path.sep)) {
    return null;
  }
  return resolved;
}

function sendPlain(response, statusCode, message) {
  response.writeHead(statusCode, { "Content-Type": "text/plain; charset=utf-8" });
  response.end(message);
}

const server = http.createServer((request, response) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    sendPlain(response, 405, "405 只支援 GET / HEAD");
    return;
  }

  const filePath = resolveRequestPath(request.url);
  if (!filePath) {
    sendPlain(response, 403, "403 路徑不在 frontend/ 目錄內");
    return;
  }

  fs.stat(filePath, (statError, stats) => {
    if (statError || !stats.isFile()) {
      sendPlain(response, 404, `404 找不到 ${request.url}`);
      console.log(`  404  ${request.url}`);
      return;
    }

    const mimeType = MIME_TYPES[path.extname(filePath).toLowerCase()] || "application/octet-stream";
    response.writeHead(200, {
      "Content-Type": mimeType,
      "Content-Length": stats.size,
      // 預覽時每次都要拿到最新檔案，避免改了畫面卻看到舊版
      "Cache-Control": "no-store",
    });

    if (request.method === "HEAD") {
      response.end();
      return;
    }

    fs.createReadStream(filePath)
      .on("error", () => sendPlain(response, 500, "500 讀取檔案失敗"))
      .pipe(response);

    console.log(`  200  ${request.url}`);
  });
});

const port = Number(process.argv[2]) || DEFAULT_PORT;

server.on("error", (error) => {
  if (error.code === "EADDRINUSE") {
    console.error(`埠號 ${port} 已被占用。換一個：node scripts/preview_frontend.js ${port + 1}`);
    process.exit(1);
  }
  throw error;
});

server.listen(port, HOST, () => {
  console.log("職涯導航家 — 前端本機預覽");
  console.log(`  根目錄　${ROOT}`);
  console.log(`  首頁　　http://${HOST}:${port}/index.html`);
  console.log(`  社群　　http://${HOST}:${port}/community.html`);
  console.log("  （Ctrl+C 結束）");
});
