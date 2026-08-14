#!/usr/bin/env node
/**
 * DeepSeekExe visual fallback. Sends a local image, URL, or clipboard image
 * to a user-configured OpenAI-compatible vision model.
 */

const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");
const os = require("os");
const { execFileSync } = require("child_process");

function loadLocalEnv() {
  const envPath = path.join(__dirname, ".env");
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const match = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (match && process.env[match[1]] === undefined) process.env[match[1]] = match[2];
  }
}

loadLocalEnv();
const BASE_URL = process.env.VISION_BASE_URL || "";
const API_KEY = process.env.VISION_API_KEY || "";
const MODEL = process.env.VISION_MODEL || "";

function parseArgs() {
  const argv = process.argv.slice(2);
  let imageSource = "";
  let prompt = "";
  let isUrl = false;
  let useClipboard = false;
  let noFallback = false;

  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--clipboard") useClipboard = true;
    else if (argv[i] === "--no-fallback") noFallback = true;
    else if (argv[i] === "--url" && argv[i + 1]) {
      isUrl = true;
      imageSource = argv[++i];
    } else if (useClipboard && !argv[i].startsWith("--")) {
      prompt = prompt ? `${prompt} ${argv[i]}` : argv[i];
    } else if (!imageSource && !argv[i].startsWith("--")) {
      imageSource = argv[i];
    } else if (imageSource && !argv[i].startsWith("--")) {
      prompt = prompt ? `${prompt} ${argv[i]}` : argv[i];
    }
  }
  if (/^https?:\/\//i.test(imageSource)) isUrl = true;
  return { imageSource, prompt: prompt || "请详细描述这张图片的内容。", isUrl, useClipboard, noFallback };
}

function readClipboardImage() {
  if (process.platform !== "win32") throw new Error("当前版本仅支持 Windows 剪贴板读取");
  const outPath = path.join(os.tmpdir(), `deepseekexe-vision-${Date.now()}.png`);
  execFileSync("powershell", ["-NoProfile", "-NonInteractive", "-Sta", "-ExecutionPolicy", "Bypass", "-File", path.join(__dirname, "clipboard.ps1"), "-OutFile", outPath], { stdio: "pipe", windowsHide: true });
  return outPath;
}

function resolveImageUrl(source, isUrl) {
  if (isUrl) return source;
  const resolved = path.resolve(source);
  if (!fs.existsSync(resolved)) throw new Error(`文件不存在: ${resolved}`);
  const ext = path.extname(resolved).toLowerCase().slice(1);
  const mime = { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", gif: "image/gif", webp: "image/webp", bmp: "image/bmp" }[ext] || "image/jpeg";
  return `data:${mime};base64,${fs.readFileSync(resolved).toString("base64")}`;
}

function request(payload) {
  const url = new URL(`${BASE_URL.replace(/\/?$/, "/")}chat/completions`);
  const body = JSON.stringify(payload);
  const transport = url.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const req = transport.request(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${API_KEY}`, "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
    }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        if (res.statusCode >= 400) return reject(new Error(`视觉 API ${res.statusCode}: ${data.slice(0, 240)}`));
        try { resolve(JSON.parse(data)?.choices?.[0]?.message?.content || data); } catch { resolve(data); }
      });
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  if (!BASE_URL || !API_KEY || !MODEL) {
    console.error("视觉模型未配置。请在 vision.js 同目录 .env 设置 VISION_BASE_URL、VISION_MODEL、VISION_API_KEY。");
    process.exit(2);
  }
  const args = parseArgs();
  let source = args.imageSource;
  if (args.useClipboard || !source || (!args.isUrl && !fs.existsSync(path.resolve(source)))) {
    if (args.noFallback && !args.useClipboard) throw new Error("未提供可用图片路径");
    source = readClipboardImage();
    args.isUrl = false;
  }
  const result = await request({
    model: MODEL,
    messages: [{ role: "user", content: [
      { type: "image_url", image_url: { url: resolveImageUrl(source, args.isUrl) } },
      { type: "text", text: args.prompt },
    ] }],
    stream: false,
    max_tokens: 1024,
  });
  console.log(result);
}

main().catch((error) => { console.error(`识图失败: ${error.message}`); process.exit(1); });
