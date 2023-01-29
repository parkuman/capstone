function handleSocket(io) {
	io.on("connection", (socket) => {
		socket.emit("server-connect-res", "yeah baby");
		console.log("server emitted shit");
	});
}

export default handleSocket;
