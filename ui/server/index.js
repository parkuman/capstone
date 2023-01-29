// server.js
import { createServer } from "http";
import express from "express";
import { Server } from "socket.io";

import { handler } from "../build/handler.js";
import handleSocket from "./handleSocket.js"

const PORT = process.env.PORT || 3000;

const app = express();
const server = createServer(app);

// Inject SocketIO

const io = new Server(server);
handleSocket(io);

// SvelteKit handlers
app.use(handler);

server.listen(PORT, () => {
	console.log(`Running on port ${PORT}`);
});
