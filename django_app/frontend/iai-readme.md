# i.AI Design System

This is a light-weight wrapper to go over the top of the gov.uk design system, adding styles for i.AI services.

## Installation

1. Import the `iai.scss` file

2. Add the i.AI logo and favicon to govuk-assets folder (or other appropriate folder for serving static files)

3. In the base layout, replace the existing favicon url with the new one

4. In the footer, replace:

```
<a class="govuk-footer__link govuk-footer__copyright-logo" href="https://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/uk-government-licensing-framework/crown-copyright/"> © Crown copyright</a>
```

With:

```
<a class="govuk-footer__link govuk-footer__copyright-logo" href="https://ai.gov.uk">
    <img src="/static/govuk-assets/i-dot-ai-Official-Logo.svg" alt="Incubator for Artificial Intelligence" loading="lazy"/>
</a>
```

## Optional styles and components

## Brand colour

The default brand colour is the i.AI pink. It is possible to change this by updating the `--product-colour` css variable at the top of the `iai.scss` file.

### Phase banner

Instead of using the standard phase banner, it is possible to add this to the header.

Replace:

```
<a href="/" class="govuk-header__link govuk-header__service-name">Service name</a>
```

With:

```
<div class="iai-header__service-name-container">
    <a href="/" class="govuk-header__link govuk-header__service-name">Service name</a>
    <strong class="govuk-tag govuk-phase-banner__content__tag">Beta</strong>
</div>
```

You may also wish to add a feedback link to the footer. Using the example at https://design-system.service.gov.uk/components/footer/#footer-with-links-and-secondary-navigation replace "Built by the Government Digital Service" with "This is a new service – your feedback will help us to improve it.".
