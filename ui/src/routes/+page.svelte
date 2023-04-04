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
	let currentSpeaker = "";
	let seconds = 0;
	let timeString = "00:00";
	let serverConnected = false;

	// TODO
	let runningTranscriptions = {};

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

				// update the seconds
				seconds++;
				const date = new Date(0);
				date.setSeconds(seconds); // specify value for SECONDS here
				timeString = date.toISOString().substring(14, 19);

				// prepend a wav header to each audio chunk (after the first one) so we can handle each as their own file
				const wav_blob = isFirstChunk
					? e.data
					: new Blob(
							[
								wavHeader(
									audioSettings.sampleSize as number,
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
		currentSpeaker = "";
		runningTranscriptions = {};
		seconds = 0;
		timeString = "00:00";
	}

	function endTranscription() {
		isRecording = false;
		mediaRecorder.stop();
		socket.emit("end_transcription");

		awaitingTranscription = true;
		currentSpeaker = "";
	}

	onMount(async () => {
		// register the wav encoder for extendable-media-recorder
		await register(await connect());

		getMicrophone();

		socket = io("http://localhost:5000/");

		socket.on("connect", () => {
			console.log("Successfully connected to server.");
			serverConnected = true;
		});

		socket.on("disconnect", function () {
			serverConnected = false;
		});

		socket.on("ready_to_receive_chunks", () => {
			// start sending audio
			mediaRecorder.start(timeSlice);
		});

		socket.on("finished_transcription", (data) => {
			console.log("finished_transcription", data);
			finalTranscription = data;
			awaitingTranscription = false;

			// on next frame (after state update), scroll to the latest transcript output
			requestAnimationFrame(() => {
				const output = document.getElementById("transcriptEnd");
				if (!output) return;
				output.scrollIntoView({
					behavior: "smooth"
				});
			});
		});

		socket.on("current_speaker", (data) => {
			console.log("current_speaker: ", data);
			currentSpeaker = data;
		});

		socket.on("transcript_update", (data) => {
			console.log("\n\nnew transcript update: ", data);

			if (runningTranscriptions[data.id]) {
				runningTranscriptions[data.id] = {
					text: data.text,
					speaker: data.speaker,
					timestamp: runningTranscriptions[data.id].timestamp
				};
			} else {
				runningTranscriptions[data.id] = {
					text: data.text,
					speaker: data.speaker,
					timestamp: timeString
				};
			}

			// on next frame (after state update), scroll to the latest transcript output
			requestAnimationFrame(() => {
				const output = document.getElementById("transcriptEnd");
				if (!output) return;
				output.scrollIntoView({
					behavior: "smooth"
				});
			});
		});
	});
</script>

<main>
	<div class="button-wrapper">
		<p style:color={serverConnected ? "green" : "red"}>
			{serverConnected ? "Connected to Backend ✅" : "Connecting to Backend..."}
		</p>
		<button
			id="record"
			title="{isRecording ? 'Stop' : 'Start'} Recording"
			on:click={isRecording ? endTranscription : beginTranscription}
			disabled={awaitingTranscription}
		>
			<!-- display stop icon if recording -->
			{#if isRecording}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					aria-hidden="true"
					class="h-8 w-8"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M5.25 7.5A2.25 2.25 0 017.5 5.25h9a2.25 2.25 0 012.25 2.25v9a2.25 2.25 0 01-2.25 2.25h-9a2.25 2.25 0 01-2.25-2.25v-9z"
					/></svg
				>
				<!-- otherwise show a microphone -->
			{:else}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					aria-hidden="true"
					class="h-8 w-8"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z"
					/></svg
				>
			{/if}
		</button>

		<div class="record-time-wrapper">
			{#if isRecording}<div class="record-animation" />{/if}
			<div class="record-time">{timeString}</div>
		</div>
	</div>

	<!-- <h1>Current Speaker</h1>
<p>{currentSpeaker}</p> -->

	<div class="live-transcript">
		<h1>Live Transcript</h1>

		{#each Object.entries(runningTranscriptions) as [id, entry] (id)}
			<div class="quote">
				<img src="/{entry.speaker}.png" loading="lazy" width="56.5" alt="" class="quote__avatar" />
				<div class="quote__content">
					<div class="quote__avatar-name">
						{entry.speaker}
						<div class="quote__time">{entry.timestamp}</div>
					</div>

					<div class="quote__text">{entry.text}</div>
				</div>
			</div>
		{/each}

		<!-- <h2>current</h2>
{#key runningTranscriptions[currentPhraseId]}
<p></p>
{/key} -->

		<!-- anchor used to scroll to -->
		<br id="transcriptEnd" />

		{#if awaitingTranscription || finalTranscription}
			<h1>Final Transcript</h1>
			{#if awaitingTranscription}
				<p>transcribing...</p>
			{/if}
		{/if}
		<p>{finalTranscription}</p>
		<!-- anchor used to scroll to -->
		<br id="finalTranscriptEnd" />
	</div>
</main>

<style>
	@import url("https://fonts.googleapis.com/css2?family=Inter&display=swap");

	:global(:root) {
		font-family: "Inter", sans-serif;
		--scale-factor: 0.6;
		background-color: #f5f8fa;
	}

	:global(html, body) {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
	}

	h1 {
		font-size: 1.5rem;
	}

	main {
	}

	.button-wrapper {
		position: sticky;
		top: 0;
		left: 0;
		background-color: #fff;
		width: 100%;
		padding: 20px;
		border-bottom: 1px solid gray;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	#record {
		width: 50px;
		height: 50px;
		border: 1px solid;
		padding: 0.5rem;
		border-radius: 9999px;
		background: none;
		cursor: pointer;
		transition: ease-in-out 0.2s;
	}

	#record:hover {
		background-color: #ffffff;
	}

	.record-time-wrapper {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
		margin-top: 10px;
	}

	.record-time {
		font-family: monospace;
	}

	@keyframes pulse {
		0% {
			opacity: 0.2;
		}
		50% {
			opacity: 1;
		}
		100% {
			opacity: 0.2;
		}
	}

	.record-animation {
		margin-right: 10px;

		background-color: rgb(255, 79, 79);
		animation: pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite;
		border-radius: 9999px;
		width: 6px;
		height: 6px;
	}

	.live-transcript {
		width: 100%;
		max-width: 90%;
		/* padding: 0 40px; */
		margin: 0 auto;
	}

	.quote {
		display: -ms-grid;
		display: grid;
		max-width: calc(45.4rem * var(--scale-factor));
		margin-bottom: calc(1.6rem * var(--scale-factor));
		/* margin-left: calc(1.6rem * var(--scale-factor)); */
		padding: calc(1.7rem * var(--scale-factor)) 1rem;
		grid-auto-columns: 1fr;
		grid-column-gap: calc(1.6rem * var(--scale-factor));
		grid-row-gap: calc(1.2rem * var(--scale-factor));
		-ms-grid-columns: auto 1fr;
		grid-template-columns: auto 1fr;
		-ms-grid-rows: auto;
		grid-template-rows: auto;
		border-radius: 24px;
		background-color: #f5f8fa;
		/* box-shadow: 0px 5px 20px rgba(130, 148, 165, 0.18); */
	}

	.quote__avatar {
		width: calc(4rem * var(--scale-factor));
	}

	.quote__content {
		padding-top: calc(0.6rem * var(--scale-factor));
	}

	.quote__avatar-name {
		font-size: calc(1.6rem * var(--scale-factor));
		line-height: 1.33;
		font-weight: 600;
	}

	.quote__time {
		display: inline;
		margin-top: calc(0.2rem * var(--scale-factor));
		margin-left: calc(0.8rem * var(--scale-factor));
		color: #8294a5;
		font-size: calc(1.2rem * var(--scale-factor));
		line-height: 1.33;
		letter-spacing: 0em;
	}

	.quote__text {
		margin-top: calc(1rem * var(--scale-factor));
		font-size: calc(1.8rem * var(--scale-factor));
	}
</style>
