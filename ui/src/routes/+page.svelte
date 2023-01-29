<script lang="ts">
  import { io, Socket } from "socket.io-client";
  import { onMount } from "svelte";

  let socket: Socket;

  onMount(() => {
    socket = io();
    socket.on("connect", () => {
      console.log("client connect!");
    });
  });
</script>

<h1>Welcome to SvelteKit</h1>
<p>Visit <a href="https://kit.svelte.dev">kit.svelte.dev</a> to read the documentation</p>
