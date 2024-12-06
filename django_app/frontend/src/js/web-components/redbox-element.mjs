/**
 * This is the base class for all Lit Elements in Redbox
 */

import { LitElement } from "lit";

export class RedboxElement extends LitElement {
  // clear the SSR content and prevents Shadow DOM by default
  createRenderRoot() {
    this.innerHTML = "";
    return this;
  }
}
