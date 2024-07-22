// @ts-check

class NewChatOptions extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `<div class="chat-options">
        <h2 class="chat-options__heading govuk-heading-m">What would you like to ask your Redbox?</h2>
        <div class="chat-options__options">
            <button class="chat-options__option chat-options__option_topic" type="button">Tell me about a specific topic</button>
            <button class="chat-options__option chat-options__option_themes" type="button">Find themes in my documents</button>
            <button class="chat-options__option chat-options__option_summarise" type="button">Summarise my document</button>
        </div>
        <p class="iai-chat-input__info-text">Or type any question below</p>
        </div>`;

        this.querySelector(".chat-options__option_topic")?.addEventListener("click", (e) => {
            this.prepopulateMessageBox("Tell me about a specific topic.");
        });
        this.querySelector(".chat-options__option_themes")?.addEventListener("click", (e) => {
            this.prepopulateMessageBox("Find themes in my documents.");
        });
        this.querySelector(".chat-options__option_summarise")?.addEventListener("click", (e) => {
            this.prepopulateMessageBox("Summarise my document.");
        });
    }

    prepopulateMessageBox = (prompt)=>{
        let chatInput = document.querySelector(".iai-chat-input__input");
        if (chatInput) {
            chatInput.value = prompt;
            chatInput.focus();
            chatInput.selectionStart = chatInput.value.length;
            this.querySelector(".chat-options")?.setAttribute("hidden", "");
        }
    }
}
customElements.define("new-chat-options", NewChatOptions);
