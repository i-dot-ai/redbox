<script>
  import Footer from "$lib/components/footer.svelte";
  import Header from "$lib/components/top-nav.svelte";

  let { data } = $props();
</script>

<Header {data} />

<main>
  <slot></slot>
</main>

<Footer />
