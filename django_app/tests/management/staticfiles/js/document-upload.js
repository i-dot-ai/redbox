(()=>{var e=globalThis,t={},a={},s=e.parcelRequire94c2;null==s&&((s=function(e){if(e in t)return t[e].exports;if(e in a){var s=a[e];delete a[e];var n={id:e,exports:{}};return t[e]=n,s.call(n.exports,n,n.exports),n.exports}var i=Error("Cannot find module '"+e+"'");throw i.code="MODULE_NOT_FOUND",i}).register=function(e,t){a[e]=t},e.parcelRequire94c2=s),(0,s.register)("795Or",function(e,t){class a extends HTMLElement{connectedCallback(){this.innerHTML=`
      <div class="rb-loading-ellipsis govuk-body-s" aria-label="${this.dataset.dataAriaLabel||this.dataset.message||"Loading"}">
        ${this.dataset.message||"Loading"}
        <span aria-hidden="true">.</span>
        <span aria-hidden="true">.</span>
        <span aria-hidden="true">.</span>
      </div>
    `}}customElements.define("loading-message",a)}),s("795Or");class n extends HTMLElement{connectedCallback(){this.closest("form")?.addEventListener("submit",()=>{this.querySelector("button")?.remove();let e=document.createElement("loading-message");e.dataset.message="Uploading",this.appendChild(e),this.setAttribute("tabindex","-1"),this.focus()})}}customElements.define("upload-button",n)})();
//# sourceMappingURL=document-upload.js.map
