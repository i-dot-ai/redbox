<script>
	import Footer from '$lib/components/footer.svelte';
	import Header from '$lib/components/top-nav.svelte';
</script>

<Header />

<main>
	<slot></slot>
</main>

<Footer />
