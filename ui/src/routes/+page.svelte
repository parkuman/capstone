<script lang="ts">
	import { io, Socket } from "socket.io-client";
	import { onMount } from "svelte";

	let timeSlice = 1000; // ms
	let socket: Socket;
	let media = [];
	let mediaRecorder = null;
	let audioSettings;

	async function getMicrophone() {
		const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		const audioTrack = stream.getAudioTracks()[0];
		audioSettings = audioTrack.getSettings();

		mediaRecorder = new MediaRecorder(stream);
		mediaRecorder.ondataavailable = (e) => {
      console.log(" - ondatavailable callback")
			socket.emit("audio_chunk", e.data);
		};

		// mediaRecorder.onstop = function () {
		// 	const audio = document.querySelector("audio");
		// 	const blob = new Blob(media, { type: "audio/ogg; codecs=opus" });
		// 	media = [];
		// 	audio.src = window.URL.createObjectURL(blob);
		// };
	}

	function beginTranscription() {
		console.log("beginTranscription() - emitting begin_transcription with: ", audioSettings);
		socket.emit("begin_transcription", audioSettings); // ask to send audio
	}

	function endTranscription() {
		mediaRecorder.stop();
    socket.emit("end_transcription");
	}

	onMount(async () => {
		getMicrophone();
		socket = io();
		socket.on("connect", () => {
			console.log("Successfully connected to server.");
		});

		socket.on("ready_to_receive_chunks", () => {
			// start sending audio
			mediaRecorder.start(timeSlice);
		});
	});
</script>

<button on:click={beginTranscription}>Record</button>
<button on:click={endTranscription}>Stop</button>
