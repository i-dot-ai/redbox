// @ts-check

// PHASE BANNER
// move to header
(() => {

    const tag = document.querySelector('.govuk-phase-banner__content__tag');
    const serviceName = document.querySelector('.govuk-header__service-name');
    if (!tag || !serviceName) {
        return;
    }

    // insert a div container around serviceName
    const header = serviceName.parentElement;
    let container = document.createElement('div');
    container.classList.add('iai-header__service-name-container');
    container.appendChild(serviceName);
    header?.prepend(container);

    container.appendChild(tag);

})();


// FOOTER
// i.AI logo + text
(() => {

    let logo = document.querySelector('.govuk-footer__copyright-logo');
    if (!logo) {
        return;
    }

    logo.textContent = '';

})();