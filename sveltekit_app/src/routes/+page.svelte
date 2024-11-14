<script>
  import Button from "$lib/components/button.svelte";

  let { data } = $props();

  // TO DO: This needs to be moved from here this is set via Waffle - would an .env be better?
  const department = "co";
</script>

<div class="rb-banner">
  <div class="govuk-width-container">
    <div class="govuk-grid-row">
      <div class="govuk-grid-column-two-thirds">
        {#if department === "uktrade"}
          <h1 class="govuk-heading-xl govuk-!-margin-bottom-7">
            Use Artificial Intelligence (AI) to interact with {data.security} level
            documents from your own document set
          </h1>
          <p class="govuk-body-l govuk-!-margin-bottom-7">
            You may summarise documents, ask questions related to one or more
            documents, and chat directly with the AI to assist you in your work.
            You can use up to, and including, Official documents.
          </p>
          <div class="rb-banner__links">
            {#if !data.userIsAuthenticated}
              <Button
                href="/sign-in"
                text="Sign in"
                classes="govuk-button--secondary govuk-!-margin-bottom-0 rb-banner__button"
              />
            {/if}
          </div>
        {:else}
          <h1 class="govuk-heading-xl govuk-!-margin-bottom-7">
            Ask any question of documents in your Redbox
          </h1>
          <p class="govuk-body-l govuk-!-margin-bottom-7">
            Use Artificial Intelligence (AI) to get insights from your personal
            document set. You can use up to, and including, {data.security} documents.
          </p>
          <div class="rb-banner__links">
            {#if !data.userIsAuthenticated}
              <Button
                href="/sign-in"
                text="Sign in"
                classes="govuk-button--secondary govuk-!-margin-bottom-0 rb-banner__button"
              />
            {/if}
            {#if data.allowSignUps && !data.userIsAuthenticated}
              <span class="govuk-body govuk-!-margin-bottom-0">
                or <a class="govuk-link" href="/sign-up-1">sign up</a> to use Redbox
              </span>
            {/if}
          </div>
        {/if}
        {#if !data.userIsAuthenticated && !data.allowSignUps}
          <p class="govuk-body govuk-!-margin-bottom-0 govuk-!-margin-top-5">
            We have paused new users signing up to Redbox. Please add your email
            to the <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSev6KZ6ASgz54GKINfk18k_Ygo_hZxcuQrS3v5XzWc4DE1gaw/viewform?usp=sharing"
              >waitlist</a
            >.
          </p>
        {/if}
      </div>
    </div>
  </div>
</div>

<div class="govuk-width-container">
  <div class="govuk-grid-row">
    <div class="govuk-grid-column-two-thirds">
      <h2 class="govuk-heading-m govuk-!-margin-top-5 govuk-!-padding-top-5">
        Upload
      </h2>
      <p class="govuk-body">
        Easily upload a wide range of document formats into your personal
        Redbox.
      </p>
      <h2 class="govuk-heading-m govuk-!-margin-top-5 govuk-!-padding-top-5">
        Chat
      </h2>
      <p class="govuk-body">
        You can communicate with your Redbox and ask questions of the documents
        contained within. Use Redbox to unlock deeper insights in the various
        documents you have uploaded, pulling together summaries of individual or
        combined documents.
      </p>
      <h2 class="govuk-heading-m govuk-!-margin-top-5 govuk-!-padding-top-5">
        Secure
      </h2>
      <p class="govuk-body">
        Redbox is built in our secure and private cloud which enables you to
        upload, up to, and including, {data.security} documents in your Redbox.
      </p>
    </div>
  </div>
</div>
