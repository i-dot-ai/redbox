// @ts-check

export class DeleteChat extends HTMLElement {

    connectedCallback() {
        this.innerHTML = `
            <button type="button">Delete</button>
        `;
        const deleteButton = this.querySelector("button");
        if (!deleteButton) {
            return;
        }
        deleteButton.addEventListener("click", async () => {
            deleteButton.disabled = true;
            await this.#requestDelete();
            if (this.dataset.iscurrentchat === "true") {
                window.location.href = "/chats";
            } else {
                deleteButton.closest("li")?.remove();
            }
        });
    }

    #requestDelete = async (newTitle) => {
        const csrfToken =
            /** @type {HTMLInputElement | null} */ (
            document.querySelector('[name="csrfmiddlewaretoken"]')
        )?.value || "";
        await fetch(`/chats/${this.dataset.chatid}/delete-chat`, {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken},
        });
    };

}

customElements.define("delete-chat", DeleteChat);
