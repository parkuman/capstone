<script lang="ts">
	import { io, Socket } from "socket.io-client";
	import { onMount } from "svelte";

	import { MediaRecorder, register } from "extendable-media-recorder";
	import { connect } from "extendable-media-recorder-wav-encoder";

	import { wavHeader } from "$lib/utils";

	let timeSlice = 1000; // ms
	let socket: Socket;
	let mediaRecorder: MediaRecorder;
	let audioSettings: MediaTrackSettings;
	let isRecording = false;
	let awaitingTranscription = false;
	let isFirstChunk = true;
	let finalTranscription = "";

	async function getMicrophone() {
		const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		const audioTrack = stream.getAudioTracks()[0];
		audioSettings = audioTrack.getSettings();

		const options = { mimeType: "audio/wav" }; // this is only allowed since we're using the extendable media recorder package
		mediaRecorder = new MediaRecorder(stream, options);

		mediaRecorder.ondataavailable = async (e) => {
			// ensures we don't send extra audio after clicking stop
			if (isRecording) {
				console.log("ondatavailable callback");

				// prepend a wav header to each audio chunk (after the first one) so we can handle each as their own file
				const wav_blob = isFirstChunk
					? e.data
					: new Blob(
							[
								wavHeader(
									audioSettings.sampleSize,
									audioSettings.channelCount,
									Infinity,
									audioSettings.sampleRate
								),
								e.data
							],
							{
								type: "audio/wav"
							}
					  );

				socket.emit("audio_chunk", wav_blob);
				isFirstChunk = false;
			}
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
		isRecording = true;
		isFirstChunk = true;
		finalTranscription = "";
	}

	function endTranscription() {
		isRecording = false;
		mediaRecorder.stop();
		socket.emit("end_transcription");
		awaitingTranscription = true;
	}

	onMount(async () => {
		// register the wav encoder for extendable-media-recorder
		await register(await connect());

		getMicrophone();

		socket = io("http://localhost:5000/");
		
		socket.on("connect", () => {
			console.log("Successfully connected to server.");
		});

		socket.on("ready_to_receive_chunks", () => {
			// start sending audio
			mediaRecorder.start(timeSlice);
		});

		socket.on("finished_transcription", (data) => {
			console.log("finished_transcription", data);
			finalTranscription = data.join("<br />");
			awaitingTranscription = false;
		});
	});
</script>

<button on:click={beginTranscription} disabled={isRecording || awaitingTranscription}>Record</button>
<button on:click={endTranscription} disabled={!isRecording || awaitingTranscription}>Stop</button>

<h1>Transcription</h1>
{#if awaitingTranscription}
	<p>transcribing...</p>
{/if}
<p>{@html finalTranscription}</p>
