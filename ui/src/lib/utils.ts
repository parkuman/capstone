/**
 * Creates a WAV header we can use to make each raw audio chunk understandable as
 * a WAV file.
 *
 * The first chunk of audio will already have this, but for subsequent ones
 * we need to add this ourselves
 *
 * See: https://github.com/chrisguttandin/extendable-media-recorder/issues/638
 * */
export const wavHeader = (bitRate: number, numberOfChannels: number, numberOfSamples: number, sampleRate = Infinity) => {
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
