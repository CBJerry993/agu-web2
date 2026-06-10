const net = require("net");
const tls = require("tls");

const REDIS_KEY = process.env.ETF_MATRIX_REDIS_KEY || "agu:etf_matrix:latest";

function encodeCommand(parts) {
  return `*${parts.length}\r\n${parts.map((part) => {
    const value = String(part);
    return `$${Buffer.byteLength(value)}\r\n${value}\r\n`;
  }).join("")}`;
}

function parseBulkString(buffer) {
  if (!buffer.length) return undefined;
  const type = String.fromCharCode(buffer[0]);

  if (type === "-") {
    const lineEnd = buffer.indexOf("\r\n");
    throw new Error(buffer.slice(1, lineEnd >= 0 ? lineEnd : undefined).toString("utf8"));
  }

  if (type === "+") {
    const lineEnd = buffer.indexOf("\r\n");
    if (lineEnd < 0) return undefined;
    return { value: null, rest: buffer.slice(lineEnd + 2), simple: true };
  }

  if (type !== "$") throw new Error("Unexpected Redis response");

  const text = buffer.toString("utf8");
  const lineEnd = text.indexOf("\r\n");
  if (lineEnd < 0) return undefined;
  const length = Number(text.slice(1, lineEnd));
  if (length === -1) return { value: null, rest: buffer.slice(lineEnd + 2) };
  if (!Number.isFinite(length) || length < 0) throw new Error("Invalid Redis bulk length");

  const start = lineEnd + 2;
  const end = start + length;
  if (buffer.length < end + 2) return undefined;
  return { value: buffer.slice(start, end).toString("utf8"), rest: buffer.slice(end + 2) };
}

function readRedisValue() {
  return new Promise((resolve, reject) => {
    const redisUrl = process.env.REDIS_URL;
    if (!redisUrl) {
      reject(new Error("REDIS_URL is not set"));
      return;
    }

    const url = new URL(redisUrl);
    const port = Number(url.port || (url.protocol === "rediss:" ? 6380 : 6379));
    const useTls = url.protocol === "rediss:";
    const password = decodeURIComponent(url.password || "");
    const username = decodeURIComponent(url.username || "");
    const db = (url.pathname || "").replace("/", "");
    const commands = [];

    if (password) {
      commands.push(username ? ["AUTH", username, password] : ["AUTH", password]);
    }
    if (db) {
      commands.push(["SELECT", db]);
    }
    commands.push(["GET", REDIS_KEY]);

    const socket = (useTls ? tls : net).connect({
      host: url.hostname,
      port,
      servername: useTls ? url.hostname : undefined,
    });

    let data = Buffer.alloc(0);
    let repliesToSkip = commands.length - 1;
    const timer = setTimeout(() => {
      socket.destroy();
      reject(new Error("Redis read timed out"));
    }, 5000);

    socket.on("connect", () => {
      socket.write(commands.map(encodeCommand).join(""));
    });

    socket.on("data", (chunk) => {
      data = Buffer.concat([data, chunk]);
      try {
        while (data.length) {
          const reply = parseBulkString(data);
          if (!reply) return;
          data = reply.rest;
          if (repliesToSkip > 0 || reply.simple) {
            repliesToSkip -= 1;
            continue;
          }

          clearTimeout(timer);
          socket.destroy();
          resolve(reply.value);
          return;
        }
      } catch (error) {
        clearTimeout(timer);
        socket.destroy();
        reject(error);
      }
    });

    socket.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });

    socket.on("end", () => {
      clearTimeout(timer);
      reject(new Error("Redis connection closed before data was read"));
    });
  });
}

exports.handler = async () => {
  try {
    const payload = await readRedisValue();
    if (!payload) {
      return {
        statusCode: 404,
        headers: { "content-type": "application/json; charset=utf-8" },
        body: JSON.stringify({ error: "ETF matrix data not found" }),
      };
    }

    JSON.parse(payload);
    return {
      statusCode: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store, max-age=0",
        "access-control-allow-origin": "*",
      },
      body: payload,
    };
  } catch (error) {
    return {
      statusCode: 500,
      headers: { "content-type": "application/json; charset=utf-8" },
      body: JSON.stringify({ error: error.message }),
    };
  }
};
