<script lang="ts">
	import { io, Socket } from "socket.io-client";
	import { onMount } from "svelte";

	import { MediaRecorder, register } from "extendable-media-recorder";
	import { connect } from "extendable-media-recorder-wav-encoder";

	let timeSlice = 1000; // ms
	let socket: Socket;
	let mediaRecorder: MediaRecorder;
	let audioSettings: MediaTrackSettings;
	let isRecording = false;
	let isFirstChunk = true;

	/**
	 * Creates a WAV header we can use to make each raw audio chunk understandable as
	 * a WAV file.
	 * 
	 * The first chunk of audio will already have this, but for subsequent ones
	 * we need to add this ourselves
	 * 
	 * See: https://github.com/chrisguttandin/extendable-media-recorder/issues/638
	 * */
	const wavHeader = (bitRate, numberOfChannels, numberOfSamples, sampleRate = Infinity) => {
		const dataView = new DataView(new ArrayBuffer(44));

		const bytesPerSample = bitRate >> 3; // tslint:disable-line:no-bitwise
		/*
		 * The maximum size of a RIFF file is 4294967295 bytes and since the header takes up 44 bytes there are 4294967251 bytes left for the
		 * data chunk.
		 */
		const dataChunkSize = Math.min(numberOfSamples * numberOfChannels * bytesPerSample, 4294967251);

		dataView.setUint32(0, 1380533830); // That's the integer representation of 'RIFF'.
		dataView.setUint32(4, dataChunkSize + 36, true);
		dataView.setUint32(8, 1463899717); // That's the integer representation of 'WAVE'.
		dataView.setUint32(12, 1718449184); // That's the integer representation of 'fmt '.
		dataView.setUint32(16, 16, true);
		dataView.setUint16(20, 1, true);
		dataView.setUint16(22, numberOfChannels, true);
		dataView.setUint32(24, sampleRate, true);
		dataView.setUint32(28, sampleRate * numberOfChannels * bytesPerSample, true);
		dataView.setUint16(32, numberOfChannels * bytesPerSample, true);
		dataView.setUint16(34, bitRate, true);
		dataView.setUint32(36, 1684108385); // That's the integer representation of 'data'.
		dataView.setUint32(40, dataChunkSize, true);

		return dataView;
	};

	async function getMicrophone() {
		// register the wav encoder for extendable-media-recorder
		await register(await connect());

		const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		const audioTrack = stream.getAudioTracks()[0];
		audioSettings = audioTrack.getSettings();

		const options = { mimeType: "audio/wav" }; // this is only allowed since we're using the extendable media recorder package
		mediaRecorder = new MediaRecorder(stream, options);

		mediaRecorder.ondataavailable = async (e) => {
			if (isRecording) {
				// ensures we don't send extra audio after clicking stop
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
	}

	function endTranscription() {
		isRecording = false;
		mediaRecorder.stop();
		socket.emit("end_transcription");
	}

	onMount(async () => {
		getMicrophone();
		socket = io("http://localhost:5000/");
		socket.on("connect", () => {
			console.log("Successfully connected to server.");
		});

		socket.on("ready_to_receive_chunks", () => {
			// start sending audio
			mediaRecorder.start(timeSlice);
		});
	});
</script>

<button on:click={beginTranscription} disabled={isRecording}>Record</button>
<button on:click={endTranscription} disabled={!isRecording}>Stop</button>
