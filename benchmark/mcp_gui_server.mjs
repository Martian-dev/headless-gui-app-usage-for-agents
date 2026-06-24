import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { z } from "zod";

const execFileAsync = promisify(execFile);
const workdir = process.env.WRITER_WORKDIR || "/workspace/run";
const display = process.env.DISPLAY || ":99";

const server = new McpServer(
  {
    name: "writer-gui-environment",
    version: "0.1.0",
  },
  {
    instructions:
      "Control LibreOffice Writer through physical GUI actions only. Use screenshot to observe the display, then click, type_text, and key to interact. Do not create files directly and do not use shell commands.",
  },
);

server.tool("screenshot", {}, async () => {
  const outputPath = path.join(workdir, "screenshot.png");
  await execFileAsync("scrot", [outputPath], { env: { ...process.env, DISPLAY: display } });
  const image = await fs.readFile(outputPath);
  return {
    content: [
      {
        type: "image",
        data: image.toString("base64"),
        mimeType: "image/png",
      },
    ],
  };
});

server.tool(
  "click",
  { x: z.number().int(), y: z.number().int(), button: z.number().int().default(1) },
  async ({ x, y, button }) => {
    await execFileAsync("xdotool", ["mousemove", String(x), String(y), "click", String(button)], {
      env: { ...process.env, DISPLAY: display },
    });
    return { content: [{ type: "text", text: `Clicked ${x},${y}` }] };
  },
);

server.tool("type_text", { text: z.string() }, async ({ text }) => {
  await execFileAsync("xdotool", ["type", "--delay", "1", text], {
    env: { ...process.env, DISPLAY: display },
  });
  return { content: [{ type: "text", text: "Typed text into the active window." }] };
});

server.tool("key", { key_name: z.string() }, async ({ key_name }) => {
  await execFileAsync("xdotool", ["key", key_name], {
    env: { ...process.env, DISPLAY: display },
  });
  return { content: [{ type: "text", text: `Pressed ${key_name}.` }] };
});

server.tool("wait", { seconds: z.number().min(0).max(10).default(1) }, async ({ seconds }) => {
  await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
  return { content: [{ type: "text", text: `Waited ${seconds} seconds.` }] };
});

await server.connect(new StdioServerTransport());
