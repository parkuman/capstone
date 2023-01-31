import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import { Readable } from "stream";
import { Blob } from "buffer";

function handleSocket(io) {
	io.on("connection", (socket) => {
		const newUUID = uuidv4();
		console.log(`Client connected with uuid: ${newUUID}`);

		const audio_chunks = [];
		const writeStream = fs.createWriteStream("test.wav");

		socket.on("begin_transcription", (audioSettings) => {
			console.log(
				"===============| begin_transcription |===============\n",
				JSON.stringify(audioSettings)
			);
			socket.emit("ready_to_receive_chunks");
		});

		socket.on("audio_chunk", (chunk) => {
			console.log("\nreceived audio chunk:\n", chunk);
			audio_chunks.push(chunk);
		});

		socket.on("end_transcription", async () => {
			console.log("===============| end_transcription |===============");
			console.log("audio_chunks:\n", audio_chunks);

			// https://stackoverflow.com/questions/60902935/how-to-save-mediarecorder-web-api-output-to-disk-using-a-stream
			console.log("saving to file...");
			const audio = new Blob(audio_chunks, { type: "audio/wav" });
			const buffer = Buffer.from(await audio.arrayBuffer());
			const readStream = Readable.from(buffer);

			readStream.pipe(writeStream).on("finish", () => {
				console.log("🎵 audio saved");
			});
		});
	});
}

export default handleSocket;
